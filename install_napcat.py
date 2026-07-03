# -*- coding: utf-8 -*-
"""
NapCat 一键安装脚本 - 自动下载、解压、配置 NapCat Shell
运行: python install_napcat.py
"""

import os
import sys
import json
import zipfile
import urllib.request
import shutil
import subprocess

# ===== 配置 =====
NAPCAT_VERSION = "v4.18.7"
NAPCAT_URL = f"https://github.com/NapNeko/NapCatQQ/releases/download/{NAPCAT_VERSION}/NapCat.Shell.zip"
NAPCAT_TARGET = os.path.join(os.path.expanduser("~"), "napcat")
QQNT_PATH = r"C:\Program Files\Tencent\QQNT"
CONFIG_SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "napcat_config.json")

def check_qq():
    """检查QQ NT是否安装"""
    qq_exe = os.path.join(QQNT_PATH, "QQ.exe")
    if os.path.exists(qq_exe):
        print(f"[OK] 检测到QQ NT: {QQNT_PATH}")
        return True
    else:
        print(f"[FAIL] 未检测到QQ NT!")
        print(f"  请安装QQ NT: https://dldir1.qq.com/qqfile/qq/QQNT/40d6045a/QQ9.9.26.44343_x64.exe")
        return False

def download_napcat():
    """下载NapCat Shell"""
    if os.path.exists(os.path.join(NAPCAT_TARGET, "NapCatWinBootMain.exe")):
        print(f"[OK] NapCat已存在于: {NAPCAT_TARGET}")
        return True

    os.makedirs(NAPCAT_TARGET, exist_ok=True)
    zip_path = os.path.join(NAPCAT_TARGET, "NapCat.Shell.zip")

    if not os.path.exists(zip_path):
        print(f"[下载] 正在下载 NapCat {NAPCAT_VERSION}...")
        print(f"  URL: {NAPCAT_URL}")
        try:
            urllib.request.urlretrieve(NAPCAT_URL, zip_path)
            size_mb = os.path.getsize(zip_path) / 1024 / 1024
            print(f"  下载完成: {size_mb:.1f} MB")
        except Exception as e:
            print(f"[FAIL] 下载失败: {e}")
            print(f"  请手动下载: {NAPCAT_URL}")
            print(f"  解压到: {NAPCAT_TARGET}")
            return False
    else:
        print(f"[OK] 已有下载文件: {zip_path}")

    print("[解压] 正在解压...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(NAPCAT_TARGET)
    os.remove(zip_path)
    print(f"[OK] 解压完成: {NAPCAT_TARGET}")
    return True

def configure_napcat():
    """写入OneBot HTTP配置"""
    config_dir = os.path.join(NAPCAT_TARGET, "config")
    os.makedirs(config_dir, exist_ok=True)
    target_config = os.path.join(config_dir, "onebot11.json")

    if os.path.exists(CONFIG_SOURCE):
        shutil.copy2(CONFIG_SOURCE, target_config)
        print(f"[OK] 配置已写入: {target_config}")
    else:
        # 直接写默认配置
        default_config = {
            "network": {
                "httpServers": [{
                    "name": "bidding-intel-http",
                    "enable": True,
                    "host": "127.0.0.1",
                    "port": 3000,
                    "messagePostFormat": "array",
                    "token": "",
                    "enableForcePushEvent": True,
                    "debug": False
                }],
                "httpClients": [],
                "websocketServers": [],
                "websocketClients": []
            },
            "musicSignUrl": "",
            "enableLocalFile2Url": True,
            "parseMultMsg": False
        }
        with open(target_config, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        print(f"[OK] 默认配置已写入: {target_config}")

def create_shortcut():
    """创建启动批处理"""
    bat_path = os.path.join(NAPCAT_TARGET, "启动NapCat.bat")
    bat_content = """@echo off
chcp 65001 >nul
title NapCat QQ Bot
echo ==========================================
echo   NapCat QQ Bot 启动
echo   HTTP API: http://127.0.0.1:3000
echo   首次使用请扫码登录QQ
echo ==========================================
cd /d "%~dp0"
NapCatWinBootMain.exe
pause
"""
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(bat_content)
    print(f"[OK] 启动脚本已创建: {bat_path}")
    return bat_path

def main():
    print("=" * 50)
    print("  NapCat QQ Bot 一键安装")
    print("=" * 50)
    print()

    # 1. 检查QQ
    if not check_qq():
        print("\n请先安装QQ NT后重试。")
        input("按回车退出...")
        sys.exit(1)

    # 2. 下载NapCat
    if not download_napcat():
        print("\n下载失败, 请手动下载。")
        input("按回车退出...")
        sys.exit(1)

    # 3. 配置
    configure_napcat()

    # 4. 创建启动脚本
    bat_path = create_shortcut()

    print()
    print("=" * 50)
    print("  安装完成!")
    print("=" * 50)
    print()
    print("接下来:")
    print(f"  1. 双击运行: {bat_path}")
    print(f"  2. 控制台会显示二维码, 用手机QQ扫码登录")
    print(f"  3. 登录成功后, 运行配置向导:")
    print(f"     cd E:\\workbuddy\\bidding-intel")
    print(f"     python notifier.py setup")
    print(f"  4. 测试推送:")
    print(f"     python notifier.py test")
    print()

    # 询问是否立即启动
    start = input("是否立即启动NapCat? (y/n): ").strip().lower()
    if start == 'y':
        print("启动NapCat...")
        os.chdir(NAPCAT_TARGET)
        subprocess.run(["NapCatWinBootMain.exe"])
    else:
        print(f"稍后启动, 双击: {bat_path}")

if __name__ == "__main__":
    main()
