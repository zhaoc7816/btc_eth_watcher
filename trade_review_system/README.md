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
├── analyze_result.py
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


## 3) 分析信号的风险与目标价

```bash
python analyze_result.py
```

脚本会读取 `data/signals.csv` 并逐条计算：

- risk
- 1R 目标价
- 2R 目标价
- 3R 目标价

如果没有记录文件，会提示：`还没有信号记录，请先运行 record_signal.py`。
如果 CSV 没有数据行，会提示：`暂无可分析的信号`。
