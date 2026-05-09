#!/usr/bin/env python3
"""统计交易信号复盘结果。"""

from __future__ import annotations

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "data" / "signals.csv"
REVIEW_STATUS = {"WIN", "LOSS", "BREAKEVEN", "CANCELLED"}
SYMBOLS = ["BTCUSDT", "ETHUSDT"]


def to_float(value: str) -> float | None:
    """把字符串安全转换为 float。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rate(numerator: int, denominator: int) -> float:
    """计算百分比，避免除零错误。"""
    if denominator == 0:
        return 0.0
    return numerator / denominator * 100


def avg(values: list[float]) -> float:
    """计算平均值。"""
    if not values:
        return 0.0
    return sum(values) / len(values)


def load_rows() -> list[dict[str, str]]:
    """读取 CSV 全部行。"""
    with CSV_FILE.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def reviewed_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """筛选出已复盘（有合法 result_status）的行。"""
    result = []
    for row in rows:
        status = row.get("result_status", "").strip().upper()
        if status in REVIEW_STATUS:
            result.append(row)
    return result


def print_overall(rows: list[dict[str, str]], reviewed: list[dict[str, str]]) -> None:
    """打印总体统计。"""
    win_count = sum(1 for r in reviewed if r.get("result_status", "").strip().upper() == "WIN")
    loss_count = sum(1 for r in reviewed if r.get("result_status", "").strip().upper() == "LOSS")
    breakeven_count = sum(1 for r in reviewed if r.get("result_status", "").strip().upper() == "BREAKEVEN")
    cancelled_count = sum(1 for r in reviewed if r.get("result_status", "").strip().upper() == "CANCELLED")

    profit_values = [v for v in (to_float(r.get("max_profit_r", "")) for r in reviewed) if v is not None]
    loss_values = [v for v in (to_float(r.get("max_loss_r", "")) for r in reviewed) if v is not None]

    print("=" * 60)
    print("总体统计")
    print("=" * 60)
    print(f"总信号数: {len(rows)}")
    print(f"已复盘信号数: {len(reviewed)}")
    print(f"WIN 数量: {win_count}")
    print(f"LOSS 数量: {loss_count}")
    print(f"BREAKEVEN 数量: {breakeven_count}")
    print(f"CANCELLED 数量: {cancelled_count}")
    print(f"胜率: {rate(win_count, len(reviewed)):.2f}%")
    print(f"平均 max_profit_r: {avg(profit_values):.4f}")
    print(f"平均 max_loss_r: {avg(loss_values):.4f}")


def print_symbol_stats(reviewed: list[dict[str, str]]) -> None:
    """按 symbol 打印统计（BTCUSDT、ETHUSDT）。"""
    print("\n" + "=" * 60)
    print("按 symbol 分组统计")
    print("=" * 60)

    for symbol in SYMBOLS:
        group = [r for r in reviewed if r.get("symbol", "").strip().upper() == symbol]
        win_count = sum(1 for r in group if r.get("result_status", "").strip().upper() == "WIN")
        profit_values = [v for v in (to_float(r.get("max_profit_r", "")) for r in group) if v is not None]
        loss_values = [v for v in (to_float(r.get("max_loss_r", "")) for r in group) if v is not None]

        print(f"\n[{symbol}]")
        print(f"信号数: {len(group)}")
        print(f"胜率: {rate(win_count, len(group)):.2f}%")
        print(f"平均 max_profit_r: {avg(profit_values):.4f}")
        print(f"平均 max_loss_r: {avg(loss_values):.4f}")


def main() -> None:
    """程序入口。"""
    if not CSV_FILE.exists():
        print("还没有信号记录，请先运行 record_signal.py")
        return

    rows = load_rows()
    reviewed = reviewed_rows(rows)

    if not reviewed:
        print("还没有复盘结果，请先运行 update_result.py")
        return

    print_overall(rows, reviewed)
    print_symbol_stats(reviewed)


if __name__ == "__main__":
    main()
