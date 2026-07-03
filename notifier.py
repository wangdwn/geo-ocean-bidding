# -*- coding: utf-8 -*-
"""
QQ消息推送模块 - 通过 OneBot 11 HTTP API 发送消息
兼容 NapCat / go-cqhttp / LLOneBot 等 OneBot 协议实现

使用前提:
  1. NapCat 已启动并登录QQ
  2. NapCat HTTP 服务已开启 (默认 127.0.0.1:3000)
  3. 在 config.json 中配置了 access_token (可选)

配置文件: E:/workbuddy/bidding-intel/notifier_config.json
"""

import requests
import json
import os
import logging
import time
import sys
from datetime import datetime

# Windows控制台UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    "napcat_http_url": "http://127.0.0.1:3000",
    "access_token": "",
    # 推送目标 - QQ号(好友)或群号
    "target_type": "private",   # private(私聊) 或 group(群聊)
    "target_id": 0,             # 你的QQ号或群号
    # 备用: Telegram 推送
    "telegram_enabled": False,
    "telegram_token": "",
    "telegram_chat_id": 0,
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notifier_config.json")


def load_config() -> dict:
    """加载推送配置"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """保存推送配置"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def send_qq_message(message: str, config: dict = None) -> bool:
    """通过 OneBot 11 HTTP API 发送QQ消息"""
    if config is None:
        config = load_config()

    if not config.get("target_id"):
        logger.warning("未配置推送目标QQ号/群号, 跳过推送")
        return False

    url = config["napcat_http_url"].rstrip("/") + "/send_msg"
    headers = {"Content-Type": "application/json"}
    if config.get("access_token"):
        headers["Authorization"] = f"Bearer {config['access_token']}"

    payload = {
        "message_type": config["target_type"],  # private 或 group
        "user_id" if config["target_type"] == "private" else "group_id": config["target_id"],
        "message": message,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        result = resp.json()
        if result.get("status") == "ok":
            logger.info(f"QQ消息推送成功 -> {config['target_type']}:{config['target_id']}")
            return True
        else:
            logger.error(f"QQ消息推送失败: {result}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error("无法连接NapCat HTTP服务, 请确认NapCat已启动。"
                    f"地址: {config['napcat_http_url']}")
        return False
    except Exception as e:
        logger.error(f"QQ消息推送异常: {e}")
        return False


def send_qq_image(image_path: str, config: dict = None) -> bool:
    """发送图片 (使用本地文件路径, NapCat支持 file:// 协议)"""
    if config is None:
        config = load_config()

    if not config.get("target_id"):
        return False

    url = config["napcat_http_url"].rstrip("/") + "/send_msg"
    headers = {"Content-Type": "application/json"}
    if config.get("access_token"):
        headers["Authorization"] = f"Bearer {config['access_token']}"

    # OneBot 11 使用 [CQ:image] 消息段
    file_uri = f"file:///{image_path.replace(os.sep, '/')}"
    cq_msg = f"[CQ:image,file={file_uri}]"

    payload = {
        "message_type": config["target_type"],
        "user_id" if config["target_type"] == "private" else "group_id": config["target_id"],
        "message": cq_msg,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        result = resp.json()
        return result.get("status") == "ok"
    except Exception as e:
        logger.error(f"QQ图片推送异常: {e}")
        return False


def send_telegram_message(message: str, config: dict = None) -> bool:
    """备用: 通过 Telegram Bot 推送"""
    if config is None:
        config = load_config()

    if not config.get("telegram_enabled"):
        return False

    url = f"https://api.telegram.org/bot{config['telegram_token']}/sendMessage"
    payload = {
        "chat_id": config["telegram_chat_id"],
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        result = resp.json()
        return result.get("ok", False)
    except Exception as e:
        logger.error(f"Telegram推送异常: {e}")
        return False


def push_weekly_report(report_path: str, summary: dict = None, config: dict = None) -> bool:
    """推送周报到QQ

    Args:
        report_path: HTML报告文件路径
        summary: 分析摘要(可选, 用于生成消息摘要)
        config: 推送配置(可选)
    """
    if config is None:
        config = load_config()

    now = datetime.now().strftime("%Y-%m-%d")

    # 构建消息摘要
    if summary and "error" not in summary:
        overview = summary.get("overview", {})
        total = overview.get("total_notices", 0)
        budget = overview.get("total_budget", 0)
        invest_count = overview.get("investment_related_count", 0)

        top_opps = summary.get("top_opportunities", [])
        top3_text = ""
        for i, opp in enumerate(top_opps[:3]):
            title = opp.get("title", "")[:40]
            score = opp.get("opportunity_score", 0)
            top3_text += f"  {i+1}. [{score}分] {title}...\n"

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
    else:
        msg = f"""📋 广东省地质海洋企业招投标情报周报
━━━━━━━━━━━━━━━━━━
📅 日期: {now}

📄 周报已生成, 请查看:
  {os.path.basename(report_path)}

━━━━━━━━━━━━━━━━━━
🤖 自动推送 | 广东省地质海洋招投标情报系统"""

    # 推送到QQ
    qq_ok = send_qq_message(msg, config)

    # 备用推送到Telegram
    if config.get("telegram_enabled"):
        send_telegram_message(msg, config)

    return qq_ok


def check_napcat_connection(config: dict = None) -> bool:
    """检查NapCat HTTP服务是否可用"""
    if config is None:
        config = load_config()

    url = config["napcat_http_url"].rstrip("/") + "/get_login_info"
    headers = {}
    if config.get("access_token"):
        headers["Authorization"] = f"Bearer {config['access_token']}"

    try:
        resp = requests.get(url, headers=headers, timeout=5)
        result = resp.json()
        if result.get("status") == "ok":
            nickname = result.get("data", {}).get("nickname", "")
            user_id = result.get("data", {}).get("user_id", 0)
            logger.info(f"NapCat连接正常, 登录账号: {nickname}({user_id})")
            return True
        return False
    except Exception:
        return False


def interactive_setup():
    """交互式配置"""
    print("=" * 50)
    print("  QQ推送配置向导")
    print("=" * 50)

    config = load_config()

    print(f"\n当前配置:")
    print(f"  NapCat地址: {config.get('napcat_http_url', '未设置')}")
    print(f"  推送类型: {config.get('target_type', '未设置')}")
    print(f"  目标ID: {config.get('target_id', '未设置')}")

    # NapCat地址
    url = input(f"\nNapCat HTTP地址 (回车保持 {config['napcat_http_url']}): ").strip()
    if url:
        config["napcat_http_url"] = url

    # access_token
    token = input(f"Access Token (回车跳过): ").strip()
    if token:
        config["access_token"] = token

    # 推送类型
    ttype = input(f"推送类型 (private/group, 回车保持 {config['target_type']}): ").strip()
    if ttype in ("private", "group"):
        config["target_type"] = ttype

    # 目标ID
    tid = input(f"目标QQ号/群号 (回车保持 {config['target_id']}): ").strip()
    if tid.isdigit():
        config["target_id"] = int(tid)

    # 测试连接
    print("\n正在测试NapCat连接...")
    if check_napcat_connection(config):
        print("✅ NapCat连接成功!")

        # 发送测试消息
        test_msg = f"✅ 推送测试成功!\n geological/marine bidding intel system 已连接。\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if send_qq_message(test_msg, config):
            print("✅ 测试消息已发送, 请检查QQ!")
        else:
            print("❌ 测试消息发送失败, 请检查目标QQ号/群号")
    else:
        print("❌ NapCat连接失败, 请确认:")
        print(f"  1. NapCat已启动并登录QQ")
        print(f"  2. HTTP服务地址正确: {config['napcat_http_url']}")
        print(f"  3. Access Token正确")

    save_config(config)
    print(f"\n配置已保存到: {CONFIG_PATH}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        interactive_setup()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        config = load_config()
        print("测试NapCat连接...")
        if check_napcat_connection(config):
            print("✅ 连接正常!")
            msg = f"🔧 推送通道测试 - {datetime.now().strftime('%H:%M:%S')}"
            send_qq_message(msg, config)
        else:
            print("❌ 连接失败, 请先启动NapCat")
    else:
        print("用法:")
        print("  python notifier.py setup  - 交互式配置")
        print("  python notifier.py test   - 测试连接和推送")
