#!/usr/bin/env python3
"""打印最近 20 条交易信号。"""

from __future__ import annotations

import csv
from pathlib import Path

# 定义数据目录和 CSV 文件路径
BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "data" / "signals.csv"


def list_latest_signals(limit: int = 20) -> None:
    """读取并打印最近 N 条信号。"""
    if not CSV_FILE.exists():
        print("还没有信号记录。请先运行 record_signal.py 添加数据。")
        return

    with CSV_FILE.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        print("signals.csv 已存在，但没有数据行。")
        return

    latest_rows = rows[-limit:]

    print(f"最近 {len(latest_rows)} 条信号（按写入顺序）：\n")
    for row in latest_rows:
        print(
            f"{row['created_at']} | {row['signal_id']} | {row['symbol']} | "
            f"{row['direction']} | entry={row['entry_price']} | "
            f"stop={row['stop_loss']} | reason={row['reason']}"
        )


def main() -> None:
    """程序入口。"""
    list_latest_signals(limit=20)


if __name__ == "__main__":
    main()
