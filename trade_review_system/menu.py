#!/usr/bin/env python3
"""交易复盘系统主菜单。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

MENU_ACTIONS = {
    "1": "record_signal.py",
    "2": "list_signals.py",
    "3": "analyze_result.py",
    "4": "update_result.py",
    "5": "stats.py",
}


def print_menu() -> None:
    """打印主菜单。"""
    print("\n=== trade_review_system 主菜单 ===")
    print("1) 记录新信号")
    print("2) 查看最近信号")
    print("3) 计算1R/2R/3R")
    print("4) 填写复盘结果")
    print("5) 查看统计结果")
    print("0) 退出")


def run_script(script_name: str) -> None:
    """执行对应脚本。"""
    script_path = BASE_DIR / script_name
    try:
        subprocess.run([sys.executable, str(script_path)], check=False)
    except Exception as exc:
        print(f"执行 {script_name} 失败: {exc}")


def main() -> None:
    """程序入口。"""
    while True:
        print_menu()
        choice = input("请输入菜单编号: ").strip()

        if choice == "0":
            print("已退出，欢迎下次使用。")
            break

        if choice in MENU_ACTIONS:
            run_script(MENU_ACTIONS[choice])
            continue

        print("输入无效，请输入 0-5 之间的数字。")


if __name__ == "__main__":
    main()
