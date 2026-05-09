#!/usr/bin/env python3
"""分析信号的 risk 和 R 倍目标价。"""

from __future__ import annotations

import csv
from pathlib import Path

# 定义 signals.csv 的路径
BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "data" / "signals.csv"


def calc_targets(direction: str, entry_price: float, stop_loss: float) -> dict[str, float]:
    """按交易方向计算 risk、1R、2R、3R。"""
    if direction == "LONG":
        risk = entry_price - stop_loss
        r1 = entry_price + risk
        r2 = entry_price + risk * 2
        r3 = entry_price + risk * 3
    else:
        risk = stop_loss - entry_price
        r1 = entry_price - risk
        r2 = entry_price - risk * 2
        r3 = entry_price - risk * 3

    return {"risk": risk, "1R": r1, "2R": r2, "3R": r3}


def analyze_signals() -> None:
    """读取 CSV 并逐条输出分析结果。"""
    if not CSV_FILE.exists():
        print("还没有信号记录，请先运行 record_signal.py")
        return

    with CSV_FILE.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        print("暂无可分析的信号")
        return

    for index, row in enumerate(rows, start=1):
        direction = row.get("direction", "").strip().upper()
        try:
            entry_price = float(row.get("entry_price", ""))
            stop_loss = float(row.get("stop_loss", ""))
        except ValueError:
            print(f"第 {index} 条数据价格格式错误，已跳过。")
            continue

        if direction not in {"LONG", "SHORT"}:
            print(f"第 {index} 条数据方向错误，已跳过。")
            continue

        result = calc_targets(direction, entry_price, stop_loss)

        print("-" * 50)
        print(f"第 {index} 条信号")
        print(f"signal_id: {row.get('signal_id', '')}")
        print(f"symbol: {row.get('symbol', '')}")
        print(f"direction: {direction}")
        print(f"entry_price: {entry_price}")
        print(f"stop_loss: {stop_loss}")
        print(f"risk: {result['risk']}")
        print(f"1R目标价: {result['1R']}")
        print(f"2R目标价: {result['2R']}")
        print(f"3R目标价: {result['3R']}")


def main() -> None:
    """程序入口。"""
    analyze_signals()


if __name__ == "__main__":
    main()
