@echo off
chcp 65001 >nul
title 招投标情报实时监控守护进程

echo ============================================================
echo   广东省地质海洋企业招投标情报 - 实时监控守护进程
echo ============================================================
echo.
echo   功能:
echo     • 每6小时自动采集最新招标公告
echo     • 发现高价值商机(评分>=70)即时推送到QQ
echo     • 每天9:00推送日报摘要
echo     • 每周一推送完整周报
echo.
echo   前提: NapCat已启动并登录QQ
echo.
echo   按 Ctrl+C 可停止守护进程
echo ============================================================
echo.

cd /d E:\workbuddy\bidding-intel
set PYTHONIOENCODING=utf-8
set PYTHONDONTWRITEBYTECODE=1

C:\Users\anybody\.workbuddy\binaries\python\envs\bidding\Scripts\python.exe monitor.py --daemon --interval 6 --threshold 70

pause
