# -*- coding: utf-8 -*-
"""
实时监控模块 - 高频采集 + 即时推送高价值商机

工作模式:
  1. 每6小时自动运行一次, 采集最近2天的新公告
  2. 分析新入库公告的商机评分
  3. 发现评分>70的高价值项目时, 立即推送到QQ
  4. 每天首次运行生成日报并推送
  5. 每周一生成完整周报并推送

运行: python monitor.py [--interval 6] [--threshold 70]
常驻: python monitor.py --daemon
"""

import sys
import os
import time
import json
import logging
import argparse
import schedule
from datetime import datetime, timedelta

# 将项目目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows控制台UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import DB_PATH, DATA_DIR, REPORT_DIR, ANALYSIS_CONFIG
from db import Database
from scraper import DataCollector
from analyzer import AnalysisEngine
from report_generator import ReportGenerator
from notifier import (send_qq_message, check_napcat_connection,
                      load_config as load_notifier_config)


def setup_logging():
    """配置日志"""
    import tempfile
    log_dir = os.path.join(tempfile.gettempdir(), "bidding_intel_logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"monitor_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ]
    )
    return logging.getLogger("monitor")


logger = setup_logging()


def collect_and_analyze(db: Database, days: int = 2) -> dict:
    """采集+分析一轮, 返回本轮统计"""
    logger.info(f"--- 开始采集 (最近{days}天) ---")

    collector = DataCollector()
    try:
        notices = collector.collect_quick(days=days)
    except Exception as e:
        logger.error(f"采集异常: {e}")
        notices = []
    finally:
        collector.close()

    if not notices:
        logger.info("本轮无新公告")
        return {"new_count": 0, "high_value": [], "total_in_db": db.get_all_notices_count()}

    new_count, update_count = db.batch_upsert_notices(notices)
    logger.info(f"采集完成: 新增 {new_count} 条, 更新 {update_count} 条")

    # 分析新公告
    engine = AnalysisEngine(db)
    engine.analyze_all_unanalyzed()

    # 获取本轮新入库且高分的公告
    # 用 collected_at 过滤本轮采集的
    recent_time = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM bidding_notices
               WHERE collected_at >= ? AND opportunity_score > 0
               ORDER BY opportunity_score DESC""",
            (recent_time,)
        ).fetchall()
    new_items = [dict(r) for r in rows]

    return {
        "new_count": new_count,
        "update_count": update_count,
        "new_items": new_items,
        "high_value": [item for item in new_items if item.get("opportunity_score", 0) >= 70],
        "medium_value": [item for item in new_items if 40 <= item.get("opportunity_score", 0) < 70],
        "total_in_db": db.get_all_notices_count(),
    }


def push_realtime_alert(high_value_items: list, stats: dict, config: dict) -> bool:
    """推送高价值商机即时告警"""
    if not high_value_items:
        return True

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 构建告警消息
    lines = []
    lines.append(f"🚨 商机即时告警")
    lines.append(f"━━━━━━━━━━━━━━━━━━")
    lines.append(f"⏰ {now}")
    lines.append(f"📊 本轮新增: {stats['new_count']} 条 | 库存: {stats['total_in_db']} 条")
    lines.append(f"🔥 高价值商机: {len(high_value_items)} 条")
    lines.append("")

    for i, item in enumerate(high_value_items[:5]):  # 最多推5条
        score = item.get("opportunity_score", 0)
        title = item.get("title", "")[:50]
        region = item.get("region", "")
        budget = item.get("budget", 0)
        budget_str = f"{budget:.0f}万" if budget else "未知"
        chain = item.get("chain_position", "")
        chain_name = {
            "upstream": "上游勘探", "midstream": "中游工程",
            "downstream": "下游服务", "investment": "招商引资"
        }.get(chain, "")

        # 关键词
        kws = []
        if item.get("matched_keywords"):
            try:
                kws = json.loads(item["matched_keywords"])[:4]
            except (json.JSONDecodeError, TypeError):
                pass
        kw_str = " ".join(f"#{k}" for k in kws)

        lines.append(f"{'🔴' if score >= 80 else '🟠'} [{score:.0f}分] {title}")
        lines.append(f"   📍 {region} | 💰 {budget_str} | 📦 {chain_name}")
        if kw_str:
            lines.append(f"   🏷 {kw_str}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("🤖 实时监控自动推送 | 地质海洋招投标情报系统")

    msg = "\n".join(lines)
    return send_qq_message(msg, config)


def push_daily_summary(db: Database, config: dict) -> bool:
    """推送每日摘要"""
    engine = AnalysisEngine(db)
    summary = engine.generate_weekly_summary(days=1)

    if "error" in summary:
        return False

    overview = summary.get("overview", {})
    today = datetime.now().strftime("%Y-%m-%d")

    # 获取今日高分项目
    top_opps = summary.get("top_opportunities", [])[:5]

    lines = []
    lines.append(f"📰 招投标日报 | {today}")
    lines.append(f"━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 今日概览:")
    lines.append(f"  • 公告数: {overview.get('total_notices', 0)} 条")
    lines.append(f"  • 总金额: {overview.get('total_budget', 0):.1f} 万元")
    lines.append(f"  • 招商引资: {overview.get('investment_related_count', 0)} 条")
    lines.append("")

    # 产业链分布
    chain_stats = summary.get("chain_stats", {})
    if chain_stats:
        lines.append("🔗 产业链分布:")
        for chain_key, chain_name in [("upstream", "上游勘探"),
                                       ("midstream", "中游工程"),
                                       ("downstream", "下游服务"),
                                       ("investment", "招商引资")]:
            if chain_key in chain_stats:
                cs = chain_stats[chain_key]
                lines.append(f"  • {chain_name}: {cs.get('count', 0)}条 / "
                           f"{(cs.get('total_budget', 0) or 0):.0f}万")
        lines.append("")

    # TOP商机
    if top_opps:
        lines.append("🔥 今日商机TOP:")
        for i, opp in enumerate(top_opps[:3]):
            score = opp.get("opportunity_score", 0)
            title = opp.get("title", "")[:40]
            lines.append(f"  {i+1}. [{score:.0f}分] {title}...")
        lines.append("")

    # 关键词热度
    keyword_freq = summary.get("keyword_freq", [])[:5]
    if keyword_freq:
        lines.append("🏷 热词: " + " ".join(f"#{k[0]}({k[1]})" for k in keyword_freq))

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("🤖 日报自动推送 | 地质海洋招投标情报系统")

    msg = "\n".join(lines)
    return send_qq_message(msg, config)


def push_weekly_full_report(db: Database, config: dict) -> bool:
    """推送完整周报"""
    engine = AnalysisEngine(db)
    summary = engine.generate_weekly_summary(days=7)
    gaps = engine.identify_chain_gaps()

    generator = ReportGenerator(REPORT_DIR, DB_PATH)
    report_path = generator.generate(summary, gaps)

    now = datetime.now().strftime("%Y-%m-%d")
    overview = summary.get("overview", {})
    total = overview.get("total_notices", 0)
    budget = overview.get("total_budget", 0)
    invest_count = overview.get("investment_related_count", 0)

    top_opps = summary.get("top_opportunities", [])
    top3_text = ""
    for i, opp in enumerate(top_opps[:3]):
        title = opp.get("title", "")[:40]
        score = opp.get("opportunity_score", 0)
        top3_text += f"  {i+1}. [{score:.0f}分] {title}...\n"

    msg = f"""📋 广东省地质海洋企业招投标情报周报
━━━━━━━━━━━━━━━━━━
📅 日期: {now}

📊 本期概览:
  • 公告总数: {total} 条
  • 涉及金额: {budget:.1f} 万元
  • 招商引资相关: {invest_count} 条

🔥 商机TOP3:
{top3_text if top3_text else "  暂无数据"}

📄 完整报告已生成:
  {os.path.basename(report_path)}

━━━━━━━━━━━━━━━━━━
🤖 自动推送 | 广东省地质海洋招投标情报系统"""

    return send_qq_message(msg, config)


def run_monitor_cycle(db: Database, config: dict, threshold: float = 70,
                      is_first_run: bool = False):
    """执行一轮监控周期"""
    now = datetime.now()
    logger.info(f"=== 监控周期开始 {now.strftime('%Y-%m-%d %H:%M:%S')} ===")

    # 采集+分析
    stats = collect_and_analyze(db, days=2)

    # 检查NapCat连接
    if not check_napcat_connection(config):
        logger.warning("NapCat未连接, 跳过推送")
        return

    # 1. 实时告警: 高价值商机
    if stats["high_value"]:
        logger.info(f"发现 {len(stats['high_value'])} 条高价值商机, 即时推送告警!")
        push_realtime_alert(stats["high_value"], stats, config)
    else:
        logger.info("本轮无高价值商机(评分>=70)")

    # 2. 每日摘要: 每天8:00-10:00之间的首次运行
    if 8 <= now.hour <= 10 and (is_first_run or not _has_pushed_today(db, "daily")):
        logger.info("推送每日摘要...")
        push_daily_summary(db, config)
        _mark_pushed(db, "daily")

    # 3. 周一推送完整周报
    if now.weekday() == 0 and 8 <= now.hour <= 10:  # 周一
        if not _has_pushed_today(db, "weekly"):
            logger.info("周一推送完整周报...")
            push_weekly_full_report(db, config)
            _mark_pushed(db, "weekly")


def _has_pushed_today(db: Database, push_type: str) -> bool:
    """检查今天是否已推送过某类型"""
    today = datetime.now().strftime("%Y-%m-%d")
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM collection_logs "
            "WHERE keyword = ? AND started_at LIKE ?",
            (f"push_{push_type}", f"{today}%")
        ).fetchone()
        return row["cnt"] > 0


def _mark_pushed(db: Database, push_type: str):
    """标记今天已推送"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.log_collection("push", f"push_{push_type}", "success")


def run_daemon(interval_hours: int = 6, threshold: float = 70):
    """守护进程模式 - 常驻运行, 定时采集+推送"""
    logger.info("=" * 60)
    logger.info("招投标情报实时监控守护进程 启动")
    logger.info(f"采集间隔: 每 {interval_hours} 小时")
    logger.info(f"告警阈值: 商机评分 >= {threshold}")
    logger.info(f"数据库: {DB_PATH}")
    logger.info("=" * 60)

    db = Database(DB_PATH)
    config = load_notifier_config()

    # 启动时立即执行一轮
    run_monitor_cycle(db, config, threshold, is_first_run=True)

    # 定时任务
    def job():
        run_monitor_cycle(db, config, threshold)

    # 每 interval_hours 小时执行一次
    schedule.every(interval_hours).hours.do(job)

    logger.info(f"守护进程已启动, 每 {interval_hours} 小时自动采集+推送")
    logger.info("按 Ctrl+C 退出")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        logger.info("守护进程已停止")


def main():
    parser = argparse.ArgumentParser(description="招投标情报实时监控")
    parser.add_argument("--daemon", action="store_true",
                        help="守护进程模式, 常驻运行")
    parser.add_argument("--interval", type=int, default=6,
                        help="采集间隔(小时), 默认6")
    parser.add_argument("--threshold", type=float, default=70,
                        help="告警阈值(商机评分), 默认70")
    parser.add_argument("--once", action="store_true",
                        help="只执行一轮后退出")
    parser.add_argument("--test-push", action="store_true",
                        help="发送测试告警")
    args = parser.parse_args()

    db = Database(DB_PATH)
    config = load_notifier_config()

    if args.test_push:
        # 测试推送
        logger.info("发送测试告警...")
        if check_napcat_connection(config):
            test_stats = {"new_count": 3, "total_in_db": db.get_all_notices_count()}
            test_items = [{
                "title": "[测试] 广州市南沙区海域地质勘探项目",
                "opportunity_score": 85.5,
                "region": "广州市",
                "budget": 3200,
                "chain_position": "upstream",
                "matched_keywords": json.dumps(["地质勘探", "海洋调查", "钻探"], ensure_ascii=False)
            }]
            ok = push_realtime_alert(test_items, test_stats, config)
            if ok:
                logger.info("测试告警推送成功!")
            else:
                logger.error("测试告警推送失败")
        else:
            logger.error("NapCat未连接")
        return

    if args.once:
        # 单次执行
        run_monitor_cycle(db, config, args.threshold, is_first_run=True)
        return

    if args.daemon:
        # 守护进程
        run_daemon(args.interval, args.threshold)
    else:
        # 默认单次
        run_monitor_cycle(db, config, args.threshold, is_first_run=True)


if __name__ == "__main__":
    main()
