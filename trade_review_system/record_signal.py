#!/usr/bin/env python3
"""记录交易信号到 CSV 文件。"""

from __future__ import annotations

import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 定义数据目录和 CSV 文件路径
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_FILE = DATA_DIR / "signals.csv"

# 定义 CSV 表头，保证写入顺序一致
FIELDNAMES = [
    "signal_id",
    "created_at",
    "symbol",
    "direction",
    "entry_price",
    "stop_loss",
    "reason",
]


def ensure_csv_ready() -> None:
    """确保 data 目录和 signals.csv 文件存在。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not CSV_FILE.exists():
        with CSV_FILE.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            writer.writeheader()


def ask_non_empty(prompt: str) -> str:
    """循环输入，直到用户提供非空内容。"""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("输入不能为空，请重试。")


def ask_direction() -> str:
    """要求用户输入 LONG 或 SHORT。"""
    while True:
        direction = input("direction (LONG/SHORT): ").strip().upper()
        if direction in {"LONG", "SHORT"}:
            return direction
        print("direction 只能是 LONG 或 SHORT，请重试。")


def ask_float(prompt: str) -> float:
    """要求用户输入数字。"""
    while True:
        raw = input(prompt).strip()
        try:
            return float(raw)
        except ValueError:
            print("请输入有效数字，例如 65000 或 3400.5")


def build_signal_record() -> dict[str, str]:
    """采集用户输入并构造一条信号记录。"""
    symbol = ask_non_empty("symbol (例如 BTCUSDT/ETHUSDT): ").upper()
    direction = ask_direction()
    entry_price = ask_float("entry_price: ")
    stop_loss = ask_float("stop_loss: ")
    reason = ask_non_empty("reason: ")

    # 生成唯一信号 ID（取 UUID 前 8 位，便于阅读）
    signal_id = f"SIG-{uuid.uuid4().hex[:8].upper()}"

    # 使用 UTC 时间，ISO 格式便于机器和人阅读
    created_at = datetime.now(timezone.utc).isoformat()

    return {
        "signal_id": signal_id,
        "created_at": created_at,
        "symbol": symbol,
        "direction": direction,
        "entry_price": f"{entry_price}",
        "stop_loss": f"{stop_loss}",
        "reason": reason,
    }


def save_signal(record: dict[str, str]) -> None:
    """将一条信号记录追加写入 CSV。"""
    with CSV_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writerow(record)


def main() -> None:
    """程序入口。"""
    ensure_csv_ready()
    record = build_signal_record()
    save_signal(record)

    print("\n信号已保存成功：")
    print(f"signal_id: {record['signal_id']}")
    print(f"created_at: {record['created_at']}")
    print(f"保存位置: {CSV_FILE}")


if __name__ == "__main__":
    main()
