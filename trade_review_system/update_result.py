#!/usr/bin/env python3
"""给已有信号补充复盘结果。"""

from __future__ import annotations

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "data" / "signals.csv"

# 复盘字段（如果原 CSV 没有，会自动补充）
RESULT_FIELDS = ["result_status", "max_profit_r", "max_loss_r", "review_note"]
VALID_STATUS = {"WIN", "LOSS", "BREAKEVEN", "CANCELLED"}


def ask_status() -> str:
    """输入并校验结果状态。"""
    while True:
        value = input("result_status (WIN/LOSS/BREAKEVEN/CANCELLED): ").strip().upper()
        if value in VALID_STATUS:
            return value
        print("请输入 WIN / LOSS / BREAKEVEN / CANCELLED 其中之一。")


def ask_float(prompt: str) -> str:
    """输入数字并返回字符串（便于写回 CSV）。"""
    while True:
        raw = input(prompt).strip()
        try:
            float(raw)
            return raw
        except ValueError:
            print("请输入有效数字，例如 1.5 或 0.6")


def load_rows() -> tuple[list[str], list[dict[str, str]]]:
    """加载 CSV 表头和数据。"""
    with CSV_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        rows = list(reader)
    return headers, rows


def ensure_headers(headers: list[str]) -> list[str]:
    """确保复盘字段都存在。"""
    new_headers = headers[:]
    for field in RESULT_FIELDS:
        if field not in new_headers:
            new_headers.append(field)
    return new_headers


def print_latest(rows: list[dict[str, str]], limit: int = 20) -> None:
    """打印最近 N 条信号，供用户选择 signal_id。"""
    print(f"最近 {min(limit, len(rows))} 条信号：")
    print("-" * 90)
    for row in rows[-limit:]:
        print(
            f"signal_id={row.get('signal_id','')} | "
            f"symbol={row.get('symbol','')} | "
            f"direction={row.get('direction','')} | "
            f"entry_price={row.get('entry_price','')} | "
            f"stop_loss={row.get('stop_loss','')} | "
            f"reason={row.get('reason','')}"
        )
    print("-" * 90)


def save_rows(headers: list[str], rows: list[dict[str, str]]) -> None:
    """把更新后的数据写回 CSV。"""
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """程序入口。"""
    if not CSV_FILE.exists():
        print("还没有信号记录，请先运行 record_signal.py")
        return

    headers, rows = load_rows()
    if not rows:
        print("暂无可更新的信号")
        return

    headers = ensure_headers(headers)
    print_latest(rows, limit=20)

    signal_id = input("请输入要更新的 signal_id: ").strip()
    target = None
    for row in rows:
        if row.get("signal_id", "").strip() == signal_id:
            target = row
            break

    if target is None:
        print("未找到对应 signal_id，未做任何修改。")
        return

    target["result_status"] = ask_status()
    target["max_profit_r"] = ask_float("max_profit_r（例如 1.5）: ")
    target["max_loss_r"] = ask_float("max_loss_r（例如 0.6）: ")
    target["review_note"] = input("review_note: ").strip()

    # 确保每行都具备所有表头字段
    for row in rows:
        for field in headers:
            row.setdefault(field, "")

    save_rows(headers, rows)
    print("更新完成，已写回 signals.csv")


if __name__ == "__main__":
    main()
