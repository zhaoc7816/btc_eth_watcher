# trade_review_system

一个简洁的 BTC/ETH 合约信号记录工具（命令行版本）。

## 环境要求

- Python 3.12

## 项目结构

```text
trade_review_system/
├── README.md
├── record_signal.py
├── list_signals.py
└── data/
    └── signals.csv  (首次记录时自动创建)
```

## 1) 记录信号

进入项目目录后运行：

```bash
python record_signal.py
```

程序会提示你输入：

- symbol（例如 `BTCUSDT` 或 `ETHUSDT`）
- direction（`LONG` 或 `SHORT`）
- entry_price
- stop_loss
- reason

保存时会自动：

- 生成 `signal_id`
- 记录 `created_at`（UTC 时间，ISO 格式）
- 若 `data/` 不存在则创建
- 若 `data/signals.csv` 不存在则创建并写入表头

## 2) 查看最近 20 条信号

```bash
python list_signals.py
```

会打印最近 20 条（不足 20 条则全部打印）。
