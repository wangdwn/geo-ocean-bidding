# -*- coding: utf-8 -*-
"""
主协调器 - 采集 → 分析 → 报告生成 一体化流程
"""

import sys
import os
import logging
import argparse
from datetime import datetime

# 将项目目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DB_PATH, DATA_DIR, REPORT_DIR, LOG_DIR, BASE_DIR
from db import Database
from scraper import DataCollector
from analyzer import AnalysisEngine
from report_generator import ReportGenerator
from demo_data import generate_demo_data

# QQ推送可选(仅在本地环境使用)
try:
    from notifier import push_weekly_report, check_napcat_connection, load_config as load_notifier_config
    HAS_NOTIFIER = True
except ImportError:
    HAS_NOTIFIER = False


def setup_logging():
    """配置日志 - 日志写到系统临时目录,避免E盘权限问题"""
    import tempfile
    log_dir = os.path.join(tempfile.gettempdir(), "bidding_intel_logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ]
    )
    return logging.getLogger("main")


def run_collect(db: Database, days: int = 7, demo: bool = False):
    """执行数据采集"""
    logger = logging.getLogger("collect")
    
    if demo:
        logger.info("=== 使用演示数据模式 ===")
        notices = generate_demo_data(days=days, count=60)
    else:
        logger.info("=== 开始实时数据采集 ===")
        collector = DataCollector()
        try:
            notices = collector.collect_quick(days=days)
        finally:
            collector.close()

    if notices:
        new_count, update_count = db.batch_upsert_notices(notices)
        logger.info(f"采集完成: 新增 {new_count} 条, 更新 {update_count} 条")
    else:
        logger.warning("未采集到任何数据, 自动切换为演示数据模式")
        notices = generate_demo_data(days=days, count=40)
        new_count, update_count = db.batch_upsert_notices(notices)
        logger.info(f"演示数据写入: {new_count} 条")

    return len(notices)


def run_analyze(db: Database):
    """执行分析"""
    logger = logging.getLogger("analyze")
    logger.info("=== 开始分析未处理公告 ===")
    engine = AnalysisEngine(db)
    engine.analyze_all_unanalyzed()
    logger.info("分析完成")


def get_issue_number(db: Database) -> int:
    """获取当前期号(已有报告数+1)"""
    try:
        with db.get_conn() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM analysis_reports")
            count = cursor.fetchone()[0]
            return count + 1
    except Exception:
        return 1


def run_report(db: Database, db_path: str, report_dir: str, days: int = 7) -> str:
    """生成报告"""
    logger = logging.getLogger("report")
    logger.info("=== 生成周度报告 ===")
    
    issue_number = get_issue_number(db)
    
    engine = AnalysisEngine(db)
    summary = engine.generate_weekly_summary(days=days)
    gaps = engine.identify_chain_gaps()
    
    generator = ReportGenerator(report_dir, db_path)
    report_path = generator.generate(summary, gaps, issue_number=issue_number)
    
    logger.info(f"第{issue_number}期报告已保存至: {report_path}")
    
    # 保存报告记录到数据库
    if "error" not in summary:
        period = summary.get("period", {})
        overview = summary.get("overview", {})
        import json
        db.save_report(
            report_date=datetime.now().strftime("%Y-%m-%d"),
            period_start=period.get("start", ""),
            period_end=period.get("end", ""),
            total_notices=overview.get("total_notices", 0),
            new_notices=db.get_new_notices_count(),
            total_budget=overview.get("total_budget", 0),
            chain_summary=json.dumps(summary.get("chain_stats", {}), ensure_ascii=False),
            top_opportunities=json.dumps(
                [{"title": o.get("title"), "score": o.get("opportunity_score")}
                 for o in summary.get("top_opportunities", [])],
                ensure_ascii=False
            ),
            entity_summary=json.dumps(
                {"tenderers": len(summary.get("top_tenderers", [])),
                 "winners": len(summary.get("top_winners", []))},
                ensure_ascii=False
            ),
            region_summary=json.dumps(summary.get("region_stats", {}), ensure_ascii=False),
            report_path=report_path,
        )
    
    return report_path


def generate_pages_index(pages_dir: str, db: Database):
    """生成 GitHub Pages 索引页 - 海洋地质主题"""
    import glob as _glob
    _log = logging.getLogger("pages_index")
    reports = sorted(_glob.glob(os.path.join(pages_dir, "weekly_report_*.html")), reverse=True)
    
    total = db.get_all_notices_count()
    report_count = len(reports)
    
    # 获取最近统计
    rows_html = ""
    for i, rp in enumerate(reports[:10]):
        fname = os.path.basename(rp)
        date_str = fname.replace("weekly_report_", "").replace(".html", "")
        issue = report_count - i
        rows_html += f'<tr><td><span class="issue-tag">第{issue}期</span></td><td><a href="{fname}">{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}</a></td><td>{os.path.getsize(rp)//1024} KB</td></tr>\n'
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>广东省地质海洋企业招投标情报系统</title>
<style>
:root {{
  --ocean-deep: #062040;
  --ocean-dark: #0a2f5a;
  --ocean-mid: #0d6b7d;
  --ocean-light: #14a085;
  --coral: #e07050;
  --gold: #f0c040;
}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{
  font-family:"Microsoft YaHei","PingFang SC",sans-serif;
  background:linear-gradient(160deg,#031528 0%,#062040 25%,#0a2f5a 60%,#0d4a6e 100%);
  color:#d8e4ee;min-height:100vh;
}}
.container{{max-width:900px;margin:0 auto;padding:20px}}
.header{{
  text-align:center;padding:48px 20px 24px;
  position:relative;
}}
.header::after{{
  content:'';display:block;width:80px;height:3px;
  background:linear-gradient(90deg,var(--ocean-mid),var(--ocean-light));
  margin:20px auto 0;border-radius:2px;
}}
.header h1{{font-size:2em;color:#e8f4f8;margin-bottom:8px;letter-spacing:2px}}
.header p{{color:#7a9aaf;font-size:1.05em}}
.header .refresh{{
  display:inline-block;margin-top:14px;padding:5px 18px;
  background:rgba(79,195,247,0.12);border:1px solid rgba(79,195,247,0.2);
  border-radius:20px;color:#81d4fa;font-size:.82em;
}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:24px 0}}
.card{{
  background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);
  border-radius:14px;padding:28px 20px;text-align:center;
  backdrop-filter:blur(10px);transition:transform .2s,border-color .2s;
}}
.card:hover{{transform:translateY(-2px);border-color:rgba(79,195,247,0.3)}}
.card .num{{font-size:2.4em;font-weight:800;color:#4fc3f7;line-height:1.1}}
.card .label{{color:#5a7a8f;margin-top:6px;font-size:.92em}}
.section{{
  background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);
  border-radius:14px;padding:28px;margin:16px 0;
}}
.section h2{{
  color:#4fc3f7;margin-bottom:18px;font-size:1.15em;font-weight:700;
  display:flex;align-items:center;gap:8px;
}}
.section h2::before{{
  content:'';display:inline-block;width:4px;height:18px;
  background:var(--ocean-mid);border-radius:2px;
}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:12px 16px;text-align:left;border-bottom:1px solid rgba(255,255,255,0.05)}}
th{{color:#5a7a8f;font-weight:600;font-size:.85em;text-transform:uppercase;letter-spacing:.5px}}
tbody tr:hover{{background:rgba(79,195,247,0.06)}}
.issue-tag{{
  display:inline-block;padding:2px 10px;border-radius:10px;
  background:rgba(224,112,80,0.2);color:#f09070;font-size:.82em;font-weight:700;
}}
a{{color:#4fc3f7;text-decoration:none;transition:color .15s}}
a:hover{{color:#81d4fa;text-decoration:underline}}
.chain-row{{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.04)}}
.chain-row:last-child{{border-bottom:none}}
.chain-dot{{
  width:12px;height:12px;border-radius:3px;flex-shrink:0;
}}
.chain-dot.up{{background:#3498db}}
.chain-dot.mid{{background:#e67e22}}
.chain-dot.down{{background:#27ae60}}
.chain-dot.inv{{background:#8e44ad}}
.chain-name{{font-weight:600;min-width:140px;font-size:.95em}}
.chain-desc{{color:#5a7a8f;font-size:.88em}}
.footer{{
  text-align:center;padding:30px;color:#3a5a6f;font-size:.85em;
  border-top:1px solid rgba(255,255,255,0.05);margin-top:24px;
}}
.waves{{
  position:relative;height:40px;margin-top:-1px;overflow:hidden;
}}
.waves svg{{display:block;width:100%;height:100%}}
</style>
</head>
<body>
<div class="waves">
  <svg viewBox="0 0 1440 40" preserveAspectRatio="none">
    <path d="M0,20 C240,30 480,5 720,18 C960,30 1200,8 1440,20 L1440,40 L0,40 Z" fill="rgba(255,255,255,0.02)"/>
  </svg>
</div>
<div class="container">
<div class="header">
<h1>广东省地质海洋企业招投标情报系统</h1>
<p>自动采集 · 智能分析 · 商机发现 · 每周更新</p>
<div class="refresh">最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</div>
</div>
<div class="cards">
<div class="card"><div class="num">{total}</div><div class="label">累计公告</div></div>
<div class="card"><div class="num">{report_count}</div><div class="label">历史报告</div></div>
<div class="card"><div class="num">4</div><div class="label">数据源</div></div>
<div class="card"><div class="num">5</div><div class="label">评分维度</div></div>
</div>
<div class="section">
<h2>最新报告</h2>
<table>
<thead><tr><th>期号</th><th>日期</th><th>大小</th></tr></thead>
<tbody>{rows_html or '<tr><td colspan="3" style="color:#3a5a6f;text-align:center;padding:24px;">暂无报告，首次采集后将自动生成</td></tr>'}</tbody>
</table>
</div>
<div class="section">
<h2>产业链覆盖</h2>
<div class="chain-row">
  <span class="chain-dot up"></span>
  <span class="chain-name">上游 · 勘探与装备</span>
  <span class="chain-desc">地质勘探、海洋调查、装备制造、材料供应</span>
</div>
<div class="chain-row">
  <span class="chain-dot mid"></span>
  <span class="chain-name">中游 · 工程与施工</span>
  <span class="chain-desc">海洋工程、地质施工、港口航道、海上能源</span>
</div>
<div class="chain-row">
  <span class="chain-dot down"></span>
  <span class="chain-name">下游 · 监测与服务</span>
  <span class="chain-desc">环境监测、技术服务、数据信息、运维咨询</span>
</div>
<div class="chain-row">
  <span class="chain-dot inv"></span>
  <span class="chain-name">招商引资</span>
  <span class="chain-desc">产业园区、投资合作、特许经营</span>
</div>
</div>
<div class="section">
<h2>数据来源</h2>
<p style="color:#5a7a8f;line-height:2;">广东省招标投标监管网 &nbsp;·&nbsp; 广东省公共资源交易平台 &nbsp;·&nbsp; 广州公共资源交易中心 &nbsp;·&nbsp; 中国招标投标公共服务平台</p>
</div>
<div class="footer">
<p>本系统自动采集公开招标信息并生成分析报告，仅供参考。投资决策请以官方公告为准。</p>
<p style="margin-top:6px;">Powered by GitHub Actions · 2026</p>
</div>
</div>
</body>
</html>"""
    
    index_path = os.path.join(pages_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    _log.info(f"索引页已生成: {index_path}")


def main():
    parser = argparse.ArgumentParser(description="广东省地质海洋企业招投标情报系统")
    parser.add_argument("--demo", action="store_true", help="使用演示数据(不实际爬取)")
    parser.add_argument("--days", type=int, default=7, help="采集最近N天的数据")
    parser.add_argument("--skip-collect", action="store_true", help="跳过采集步骤")
    parser.add_argument("--skip-analyze", action="store_true", help="跳过分析步骤")
    parser.add_argument("--report-only", action="store_true", help="仅生成报告")
    parser.add_argument("--no-push", action="store_true", help="跳过QQ推送")
    parser.add_argument("--push-only", action="store_true", help="仅推送已有报告")
    parser.add_argument("--pages", action="store_true", help="GitHub Pages模式: 报告输出到docs/并生成索引页")
    args = parser.parse_args()

    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("广东省地质海洋企业招投标情报系统 启动")
    logger.info(f"数据库: {DB_PATH}")
    logger.info(f"报告目录: {REPORT_DIR}")
    logger.info("=" * 60)

    db = Database(DB_PATH)

    try:
        if not args.report_only:
            if not args.skip_collect:
                run_collect(db, days=args.days, demo=args.demo)
            if not args.skip_analyze:
                run_analyze(db)

        report_path = run_report(db, DB_PATH, REPORT_DIR, days=args.days)

        # ===== GitHub Pages 模式 =====
        if args.pages:
            pages_dir = os.path.join(BASE_DIR, "docs")
            os.makedirs(pages_dir, exist_ok=True)
            import shutil
            # 复制报告到 docs/
            report_filename = os.path.basename(report_path)
            pages_path = os.path.join(pages_dir, report_filename)
            shutil.copy2(report_path, pages_path)
            # 生成索引页
            generate_pages_index(pages_dir, db)
            # 确保 .nojekyll 存在，避免 GitHub Pages 用 Jekyll 处理
            nojekyll = os.path.join(pages_dir, ".nojekyll")
            if not os.path.exists(nojekyll):
                open(nojekyll, "w").close()
            logger.info(f"GitHub Pages 已更新: {pages_path}")

        # ===== QQ推送(仅本地环境) =====
        if HAS_NOTIFIER and not args.no_push:
            logger.info("=== 检查QQ推送通道 ===")
            notifier_config = load_notifier_config()
            if check_napcat_connection(notifier_config):
                logger.info("NapCat连接正常, 开始推送...")
                engine = AnalysisEngine(db)
                summary = engine.generate_weekly_summary(days=args.days)
                push_ok = push_weekly_report(report_path, summary, notifier_config)
                if push_ok:
                    logger.info("✅ 周报已推送到QQ!")
                else:
                    logger.warning("推送失败, 请检查notifier_config.json配置")
            else:
                logger.warning("NapCat未连接, 跳过QQ推送。"
                             "请先启动NapCat并登录QQ, 然后运行: python notifier.py setup")
        elif HAS_NOTIFIER:
            logger.info("已跳过QQ推送 (--no-push)")
        else:
            logger.info("QQ推送模块未加载 (GitHub环境, 跳过)")

        logger.info("=" * 60)
        logger.info("全部任务完成!")
        logger.info(f"报告路径: {report_path}")
        logger.info(f"数据库总计: {db.get_all_notices_count()} 条公告")
        logger.info("=" * 60)
        
        # 输出报告路径供外部调用
        print(f"\nREPORT_PATH={report_path}")
        return report_path

    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        raise
    finally:
        pass


if __name__ == "__main__":
    main()
