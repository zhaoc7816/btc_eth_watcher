#!/usr/bin/env python3
"""分析信号的风险与 R 倍数目标价。"""

from __future__ import annotations

import csv
from pathlib import Path

# 定义 CSV 文件路径
BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "data" / "signals.csv"


def calc_targets(direction: str, entry_price: float, stop_loss: float) -> dict[str, float]:
    """根据方向计算 risk、1R、2R、3R。"""
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

    return {
        "risk": risk,
        "1R": r1,
        "2R": r2,
        "3R": r3,
    }


def analyze_signals() -> None:
    """读取 CSV 并打印每条信号的分析结果。"""
    if not CSV_FILE.exists():
        print("还没有信号记录，请先运行 record_signal.py")
        return

    with CSV_FILE.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        print("暂无可分析的信号")
        return

    print(f"共读取到 {len(rows)} 条信号，分析结果如下：\n")

    for idx, row in enumerate(rows, start=1):
        try:
            entry_price = float(row["entry_price"])
            stop_loss = float(row["stop_loss"])
            direction = row["direction"].strip().upper()
        except (KeyError, ValueError):
            print(f"第 {idx} 条数据格式异常，已跳过。")
            continue

        if direction not in {"LONG", "SHORT"}:
            print(f"第 {idx} 条 direction 非 LONG/SHORT，已跳过。")
            continue

        result = calc_targets(direction, entry_price, stop_loss)

        # 用分隔线让新手更容易阅读每条记录
        print("-" * 60)
        print(f"第 {idx} 条信号")
        print(f"signal_id : {row.get('signal_id', 'N/A')}")
        print(f"created_at: {row.get('created_at', 'N/A')}")
        print(f"symbol    : {row.get('symbol', 'N/A')}")
        print(f"direction : {direction}")
        print(f"entry     : {entry_price:.6f}")
        print(f"stop_loss : {stop_loss:.6f}")
        print(f"risk      : {result['risk']:.6f}")
        print(f"1R 目标价 : {result['1R']:.6f}")
        print(f"2R 目标价 : {result['2R']:.6f}")
        print(f"3R 目标价 : {result['3R']:.6f}")

    print("-" * 60)


def main() -> None:
    """程序入口。"""
    analyze_signals()


if __name__ == "__main__":
    main()
