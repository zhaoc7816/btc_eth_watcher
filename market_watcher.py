import ccxt
import pandas as pd
from datetime import datetime, timezone, timedelta
from dingtalk_test import load_env, send_dingtalk_markdown


SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
TIMEFRAME = "15m"
LIMIT = 160


def now_beijing():
    bj = datetime.now(timezone.utc) + timedelta(hours=8)
    return bj.strftime("%Y-%m-%d %H:%M:%S")


def fetch_ohlcv(symbol):
    exchange = ccxt.okx({
        "enableRateLimit": True,
        "options": {
            "defaultType": "swap"
        }
    })

    data = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=LIMIT)

    df = pd.DataFrame(
        data,
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )

    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["datetime_bj"] = df["datetime"] + pd.Timedelta(hours=8)

    return df


def fetch_ohlcv_tf(symbol, timeframe, limit=160):
    exchange = ccxt.okx({
        "enableRateLimit": True,
        "options": {
            "defaultType": "swap"
        }
    })

    data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    df = pd.DataFrame(
        data,
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )

    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["datetime_bj"] = df["datetime"] + pd.Timedelta(hours=8)

    return df


def add_indicators(df):
    df["ma5"] = df["close"].rolling(5).mean()
    df["ma10"] = df["close"].rolling(10).mean()
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma30"] = df["close"].rolling(30).mean()
    df["ma60"] = df["close"].rolling(60).mean()

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd_diff"] = ema12 - ema26
    df["macd_dea"] = df["macd_diff"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd_diff"] - df["macd_dea"]

    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    df["vwap"] = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()

    return df


def volume_state(last, prev):
    volume = last["volume"]
    prev_volume = prev["volume"]

    if volume > prev_volume * 1.3:
        return "放量"
    elif volume < prev_volume * 0.7:
        return "缩量"
    else:
        return "正常"


def detect_model(df):
    last = df.iloc[-2]
    prev = df.iloc[-3]

    price = last["close"]
    ma5 = last["ma5"]
    ma10 = last["ma10"]
    ma20 = last["ma20"]
    ma30 = last["ma30"]
    ma60 = last["ma60"]
    rsi = last["rsi"]
    macd_hist = last["macd_hist"]
    vwap = last["vwap"]

    vol_state = volume_state(last, prev)

    ma_bull = ma5 > ma10 > ma20 > ma60
    ma_bear = ma5 < ma10 < ma20 < ma60
    near_ma20 = abs(price - ma20) / price <= 0.003

    # 模型1：强多趋势盘
    if price > ma20 > ma60 and ma_bull and rsi >= 55 and macd_hist > 0:
        return {
            "model": "模型1 强多趋势盘",
            "direction": "LONG",
            "status": "WATCH",
            "status_text": "👀【观察接近】",
            "trigger": "等待价格回踩 MA20，15m 不破并重新转强",
            "allow_action": "回踩 MA20 不破后试多",
            "forbid_action": "禁止当前位置追多，禁止抄顶空",
            "risk": "跌破 MA20，强多结构降级"
        }

    # 模型2：多头回踩盘
    if price > ma60 and near_ma20 and 42 <= rsi <= 58 and macd_hist >= 0:
        if price > ma20 and vol_state != "缩量":
            status = "ALLOW"
            status_text = "✅【允许出手】"
            trigger = "15m 已在 MA20 上方，成交量未明显缩量"
            allow_action = "小仓试多，止损放在确认K低点下方"
        else:
            status = "WATCH"
            status_text = "👀【观察接近】"
            trigger = "等待 15m 收回 MA20 上方，且成交量不缩"
            allow_action = "回踩 MA20 不破后再试多"

        return {
            "model": "模型2 多头回踩盘",
            "direction": "LONG",
            "status": status,
            "status_text": status_text,
            "trigger": trigger,
            "allow_action": allow_action,
            "forbid_action": "禁止提前满仓，禁止跌破 MA20 后硬多",
            "risk": "放量跌破 MA20，回踩失败"
        }

    # 模型3：弱修复盘
    if price > ma60 and price < ma20 and ma20 < ma30 and 38 <= rsi <= 52:
        return {
            "model": "模型3 弱修复盘",
            "direction": "WAIT",
            "status": "BLOCK",
            "status_text": "❌【禁止出手】",
            "trigger": "等待重新站回 MA20，或者反抽失败再判断",
            "allow_action": "只观察，不主动开仓",
            "forbid_action": "禁止在 MA20 下方盲目做多",
            "risk": "容易假突破，容易来回扫"
        }

    # 模型6：强空趋势盘
    if price < ma20 < ma60 and ma_bear and rsi <= 45 and macd_hist < 0:
        return {
            "model": "模型6 强空趋势盘",
            "direction": "SHORT",
            "status": "WATCH",
            "status_text": "👀【观察接近】",
            "trigger": "等待反抽 MA20 失败，15m 收阴确认",
            "allow_action": "反抽 MA20 失败后试空",
            "forbid_action": "禁止当前位置追空，禁止抄底多",
            "risk": "重新站上 MA20，强空结构降级"
        }

    # 模型5：空头反抽盘
    if price < ma60 and near_ma20 and 40 <= rsi <= 58 and macd_hist <= 0:
        if price < ma20 and vol_state != "缩量":
            status = "ALLOW"
            status_text = "✅【允许出手】"
            trigger = "15m 反抽 MA20 未站稳，空头动能仍在"
            allow_action = "小仓试空，止损放在确认K高点上方"
        else:
            status = "WATCH"
            status_text = "👀【观察接近】"
            trigger = "等待反抽 MA20 失败，15m 收阴确认"
            allow_action = "反抽失败后再试空"

        return {
            "model": "模型5 空头反抽盘",
            "direction": "SHORT",
            "status": status,
            "status_text": status_text,
            "trigger": trigger,
            "allow_action": allow_action,
            "forbid_action": "禁止当前位置追空，禁止直接抄底多",
            "risk": "站上 MA20 并放量，空头反抽失败"
        }

    # 模型4：震荡盘
    return {
        "model": "模型4 震荡盘",
        "direction": "WAIT",
        "status": "BLOCK",
        "status_text": "❌【禁止出手】",
        "trigger": "等待箱体边缘或新结构出现",
        "allow_action": "只看箱体边缘，不做中间位置",
        "forbid_action": "禁止中间位置开仓，禁止看一根K线冲动下单",
        "risk": "震荡盘最容易被假突破来回扫"
    }


def build_signal_card(symbol, df, model):
    last = df.iloc[-2]
    prev = df.iloc[-3]

    price = last["close"]
    ma20 = last["ma20"]
    ma60 = last["ma60"]
    rsi = last["rsi"]
    macd_hist = last["macd_hist"]
    vwap = last["vwap"]
    vol_state = volume_state(last, prev)
    execution_plan = build_execution_plan(symbol, model, df)

    macd_state = "多头动能" if macd_hist > 0 else "空头动能"

    card = f"""
{model["status_text"]} {symbol}

时间：{last["datetime_bj"]}
周期：{TIMEFRAME}
当前价：{price:.2f}

模型：{model["model"]}
方向：{model["direction"]}
状态：{model["status"]}

MA20：{ma20:.2f}
MA60：{ma60:.2f}
RSI：{rsi:.2f}
VWAP：{vwap:.2f}
MACD：{macd_state}
成交量：{vol_state}

触发条件：
{model["trigger"]}

允许动作：
{model["allow_action"]}

禁止动作：
{model["forbid_action"]}

BTC领航过滤：
{model.get("leader_filter", "未启用")}

MA20区域过滤：
{model.get("ma20_zone_filter", "未启用")}

大周期过滤：
{model.get("htf_filter", "未启用")}

资金四确认：
{model.get("flow_filter", "未启用")}

风险提示：
{model["risk"]}

交易执行单：
{execution_plan}
"""
    return card



def get_btc_leader_bias(btc_model):
    model_name = btc_model["model"]
    direction = btc_model["direction"]

    if direction == "LONG" and ("模型1" in model_name or "模型2" in model_name):
        return {
            "bias": "LONG",
            "text": "BTC 领航偏多，市场环境支持多头进攻或回踩多"
        }

    if direction == "SHORT" and ("模型5" in model_name or "模型6" in model_name):
        return {
            "bias": "SHORT",
            "text": "BTC 领航偏空，市场环境支持反抽空或趋势空"
        }

    return {
        "bias": "WAIT",
        "text": "BTC 领航不明确，市场环境不支持激进出手"
    }


def apply_btc_leader_filter(symbol, model, btc_leader):
    if "BTC" in symbol:
        model["leader_filter"] = "BTC 自身作为领航，不需要过滤"
        return model

    eth_direction = model["direction"]
    btc_bias = btc_leader["bias"]

    model["leader_filter"] = btc_leader["text"]

    if model["status"] == "ALLOW":
        if eth_direction == "LONG" and btc_bias != "LONG":
            model["status"] = "WATCH"
            model["status_text"] = "👀【观察接近】"
            model["trigger"] = model["trigger"] + "；但 BTC 领航不支持多头，信号降级"
            model["allow_action"] = "BTC 未确认偏多前，ETH 不主动开多"
            model["risk"] = "ETH 单独走强但 BTC 不配合，容易假突破"

        elif eth_direction == "SHORT" and btc_bias != "SHORT":
            model["status"] = "WATCH"
            model["status_text"] = "👀【观察接近】"
            model["trigger"] = model["trigger"] + "；但 BTC 领航不支持空头，信号降级"
            model["allow_action"] = "BTC 未确认偏空前，ETH 不主动开空"
            model["risk"] = "ETH 单独走弱但 BTC 不配合，容易假跌破"

    return model



def detect_htf_bias(symbol):
    """
    大周期过滤：
    1H = 中短结构
    4H = 大方向风险
    LONG  = 大周期偏多
    SHORT = 大周期偏空
    WAIT  = 大周期震荡/不明确
    """
    result = {}

    for tf in ["1h", "4h"]:
        try:
            df = fetch_ohlcv_tf(symbol, tf, 160)
            df = add_indicators(df)
            last = df.iloc[-2]

            price = last["close"]
            ma20 = last["ma20"]
            ma60 = last["ma60"]
            rsi = last["rsi"]
            macd_hist = last["macd_hist"]

            if price > ma20 > ma60 and macd_hist > 0 and rsi >= 50:
                bias = "LONG"
                text = f"{tf} 偏多：价格在 MA20/MA60 上方，动能偏多"
            elif price < ma20 < ma60 and macd_hist < 0 and rsi <= 50:
                bias = "SHORT"
                text = f"{tf} 偏空：价格在 MA20/MA60 下方，动能偏空"
            else:
                bias = "WAIT"
                text = f"{tf} 震荡/修复：方向不够干净"

            result[tf] = {
                "bias": bias,
                "text": text,
                "price": price,
                "ma20": ma20,
                "ma60": ma60,
                "rsi": rsi,
                "macd_hist": macd_hist
            }

        except Exception as e:
            result[tf] = {
                "bias": "WAIT",
                "text": f"{tf} 获取失败，默认降级观察：{e}",
                "price": 0,
                "ma20": 0,
                "ma60": 0,
                "rsi": 0,
                "macd_hist": 0
            }

    return result


def apply_htf_filter(symbol, model, htf_bias):
    """
    1H / 4H 大周期过滤：
    LONG 信号不能逆 1H/4H 空头
    SHORT 信号不能逆 1H/4H 多头
    """
    direction = model["direction"]
    status = model["status"]

    h1 = htf_bias.get("1h", {}).get("bias", "WAIT")
    h4 = htf_bias.get("4h", {}).get("bias", "WAIT")

    htf_text = (
        f"1H：{htf_bias.get('1h', {}).get('text', '无')}\n"
        f"4H：{htf_bias.get('4h', {}).get('text', '无')}"
    )

    model["htf_filter"] = htf_text

    if status == "ALLOW":
        if direction == "LONG" and (h1 == "SHORT" or h4 == "SHORT"):
            model["status"] = "WATCH"
            model["status_text"] = "👀【观察接近】"
            model["trigger"] = model["trigger"] + "；但 1H/4H 大周期不支持多头，信号降级"
            model["allow_action"] = "大周期未转多前，不主动开多"
            model["risk"] = "15m 多头信号逆大周期，容易冲高回落"

        elif direction == "SHORT" and (h1 == "LONG" or h4 == "LONG"):
            model["status"] = "WATCH"
            model["status_text"] = "👀【观察接近】"
            model["trigger"] = model["trigger"] + "；但 1H/4H 大周期不支持空头，信号降级"
            model["allow_action"] = "大周期未转空前，不主动开空"
            model["risk"] = "15m 空头信号逆大周期，容易假跌破反拉"

    return model



def fetch_open_interest_safe(symbol):
    """
    获取 OKX 永续合约 OI。
    如果获取失败，不让程序崩溃，返回 None。
    """
    try:
        exchange = ccxt.okx({
            "enableRateLimit": True,
            "options": {
                "defaultType": "swap"
            }
        })

        oi = exchange.fetch_open_interest(symbol)

        value = (
            oi.get("openInterestAmount")
            or oi.get("openInterestValue")
            or oi.get("openInterest")
        )

        if value is None:
            return None

        return float(value)

    except Exception:
        return None


def fetch_open_interest_history_safe(symbol, timeframe="15m", limit=5):
    """
    获取 OI 历史，用于比较上一根与当前 OI 的变化。
    如果交易所接口不支持或失败，则返回 None。
    """
    try:
        exchange = ccxt.okx({
            "enableRateLimit": True,
            "options": {
                "defaultType": "swap"
            }
        })

        data = exchange.fetch_open_interest_history(symbol, timeframe=timeframe, limit=limit)

        values = []
        for item in data:
            value = (
                item.get("openInterestAmount")
                or item.get("openInterestValue")
                or item.get("openInterest")
            )

            if value is not None:
                values.append(float(value))

        if len(values) < 2:
            return None

        return values

    except Exception:
        return None


def get_volume_confirm(last, prev):
    volume = last["volume"]
    prev_volume = prev["volume"]

    if volume > prev_volume * 1.3:
        return {
            "state": "STRONG",
            "text": "成交量放大，支持信号"
        }

    if volume < prev_volume * 0.7:
        return {
            "state": "WEAK",
            "text": "成交量缩小，信号质量下降"
        }

    return {
        "state": "NORMAL",
        "text": "成交量正常，未明显拖累信号"
    }


def get_vwap_confirm(direction, price, vwap):
    if direction == "LONG":
        if price > vwap:
            return {
                "state": "PASS",
                "text": f"价格在 VWAP 上方，多头站位合理，VWAP={vwap:.2f}"
            }
        return {
            "state": "FAIL",
            "text": f"价格在 VWAP 下方，多头站位不足，VWAP={vwap:.2f}"
        }

    if direction == "SHORT":
        if price < vwap:
            return {
                "state": "PASS",
                "text": f"价格在 VWAP 下方，空头站位合理，VWAP={vwap:.2f}"
            }
        return {
            "state": "FAIL",
            "text": f"价格在 VWAP 上方，空头站位不足，VWAP={vwap:.2f}"
        }

    return {
        "state": "NEUTRAL",
        "text": f"无方向信号，VWAP={vwap:.2f}"
    }


def get_oi_confirm(symbol, direction, last, prev):
    """
    V7.1 OI 前后对比确认。

    LONG：
    价格上涨 + OI 增加 = 多头主动进场，PASS
    价格上涨 + OI 下降 = 空头平仓推动，WEAK

    SHORT：
    价格下跌 + OI 增加 = 空头主动进场，PASS
    价格下跌 + OI 下降 = 多头平仓/止损，WEAK
    """
    history = fetch_open_interest_history_safe(symbol, TIMEFRAME, 5)

    price_now = last["close"]
    price_prev = prev["close"]

    if history is None:
        oi_now = fetch_open_interest_safe(symbol)

        if oi_now is None:
            return {
                "state": "UNKNOWN",
                "text": "OI 历史获取失败，本轮不作为强过滤"
            }

        return {
            "state": "UNKNOWN",
            "text": f"OI 当前值：{oi_now:.2f}，历史对比暂不可用，本轮不强过滤"
        }

    oi_prev = history[-2]
    oi_now = history[-1]

    oi_change_pct = (oi_now - oi_prev) / oi_prev if oi_prev else 0
    price_change_pct = (price_now - price_prev) / price_prev if price_prev else 0

    if oi_change_pct > 0.003:
        oi_state = "UP"
        oi_desc = "OI 增加"
    elif oi_change_pct < -0.003:
        oi_state = "DOWN"
        oi_desc = "OI 下降"
    else:
        oi_state = "FLAT"
        oi_desc = "OI 变化不明显"

    price_desc = "价格上涨" if price_change_pct > 0 else "价格下跌" if price_change_pct < 0 else "价格横盘"

    if direction == "LONG":
        if price_change_pct > 0 and oi_state == "UP":
            return {
                "state": "PASS",
                "text": f"{price_desc} + {oi_desc}，多头主动进场。OI：{oi_prev:.2f} → {oi_now:.2f}"
            }

        if price_change_pct > 0 and oi_state == "DOWN":
            return {
                "state": "WEAK",
                "text": f"{price_desc} + {oi_desc}，更像空头平仓推动，多头质量下降。OI：{oi_prev:.2f} → {oi_now:.2f}"
            }

        return {
            "state": "NORMAL",
            "text": f"{price_desc} + {oi_desc}，多头确认一般。OI：{oi_prev:.2f} → {oi_now:.2f}"
        }

    if direction == "SHORT":
        if price_change_pct < 0 and oi_state == "UP":
            return {
                "state": "PASS",
                "text": f"{price_desc} + {oi_desc}，空头主动进场。OI：{oi_prev:.2f} → {oi_now:.2f}"
            }

        if price_change_pct < 0 and oi_state == "DOWN":
            return {
                "state": "WEAK",
                "text": f"{price_desc} + {oi_desc}，更像多头平仓/止损，空头质量下降。OI：{oi_prev:.2f} → {oi_now:.2f}"
            }

        return {
            "state": "NORMAL",
            "text": f"{price_desc} + {oi_desc}，空头确认一般。OI：{oi_prev:.2f} → {oi_now:.2f}"
        }

    return {
        "state": "NEUTRAL",
        "text": f"当前无方向信号，OI：{oi_prev:.2f} → {oi_now:.2f}"
    }


def apply_flow_filter(symbol, model, df):
    """
    V7 三确认：
    OI + 成交量 + VWAP。
    只对 ALLOW 信号做强过滤。
    不满足则降级 WATCH。
    """
    last = df.iloc[-2]
    prev = df.iloc[-3]

    price = last["close"]
    vwap = last["vwap"]
    direction = model["direction"]

    vol_confirm = get_volume_confirm(last, prev)
    vwap_confirm = get_vwap_confirm(direction, price, vwap)
    oi_confirm = get_oi_confirm(symbol, direction, last, prev)

    flow_text = (
        f"OI：{oi_confirm['text']}\n"
        f"VOL：{vol_confirm['text']}\n"
        f"VWAP：{vwap_confirm['text']}"
    )

    model["flow_filter"] = flow_text

    if model["status"] == "ALLOW":
        fail_reasons = []

        if vol_confirm["state"] == "WEAK":
            fail_reasons.append("成交量缩量")

        if oi_confirm["state"] == "WEAK":
            fail_reasons.append("OI不支持")

        if direction in ["LONG", "SHORT"] and vwap_confirm["state"] == "FAIL":
            fail_reasons.append("VWAP站位不支持")

        if fail_reasons:
            model["status"] = "WATCH"
            model["status_text"] = "👀【观察接近】"
            model["trigger"] = model["trigger"] + "；但资金确认不足，信号降级"
            model["allow_action"] = "等待 Price / OI / VOL / VWAP 四确认重新转强后再出手"
            model["risk"] = "结构信号有，但资金确认不足，容易假突破/假跌破：" + "、".join(fail_reasons)

    return model




def detect_ma20_zone_state(df, tolerance=0.0025):
    """
    V8.1 MA20 区域判断：
    - MA20 ±0.25% 视为纠缠区
    - 连续2根收在 MA20 上方，才算有效站上
    - 连续2根收在 MA20 下方，才算有效跌破
    - 单根穿越不作为开仓依据
    """
    last = df.iloc[-2]
    prev = df.iloc[-3]

    close = last["close"]
    prev_close = prev["close"]

    ma20 = last["ma20"]
    prev_ma20 = prev["ma20"]

    distance = abs(close - ma20) / close if close else 0

    last_above = close > ma20
    last_below = close < ma20
    prev_above = prev_close > prev_ma20
    prev_below = prev_close < prev_ma20

    in_zone = distance <= tolerance

    if in_zone:
        return {
            "state": "MA20_CHOP_ZONE",
            "text": f"MA20 纠缠区：价格距离 MA20 约 {distance*100:.2f}%，禁止追多追空",
            "bias": "WAIT"
        }

    if prev_above and last_above:
        return {
            "state": "CONFIRMED_ABOVE",
            "text": f"MA20 有效站上：连续2根15m收在 MA20 上方，距离约 {distance*100:.2f}%",
            "bias": "LONG"
        }

    if prev_below and last_below:
        return {
            "state": "CONFIRMED_BELOW",
            "text": f"MA20 有效跌破：连续2根15m收在 MA20 下方，距离约 {distance*100:.2f}%",
            "bias": "SHORT"
        }

    if prev_below and last_above:
        return {
            "state": "FALSE_BREAKDOWN",
            "text": "MA20 假跌破：上一根在 MA20 下方，本根重新收回 MA20 上方",
            "bias": "WATCH_LONG"
        }

    if prev_above and last_below:
        return {
            "state": "FALSE_BREAKOUT",
            "text": "MA20 假突破：上一根在 MA20 上方，本根重新跌回 MA20 下方",
            "bias": "WATCH_SHORT"
        }

    if last_above:
        return {
            "state": "SINGLE_ABOVE",
            "text": "单根收在 MA20 上方，但还没有连续2根确认",
            "bias": "WATCH_LONG"
        }

    if last_below:
        return {
            "state": "SINGLE_BELOW",
            "text": "单根收在 MA20 下方，但还没有连续2根确认",
            "bias": "WATCH_SHORT"
        }

    return {
        "state": "UNKNOWN",
        "text": "MA20 状态不明确",
        "bias": "WAIT"
    }


def apply_ma20_zone_filter(symbol, model, df):
    """
    V8.1 MA20 区域过滤：
    只对 ALLOW 信号做强过滤。
    如果处于 MA20 纠缠区，禁止直接 ALLOW。
    """
    ma20_state = detect_ma20_zone_state(df)
    model["ma20_zone_filter"] = ma20_state["text"]

    direction = model["direction"]
    status = model["status"]
    state = ma20_state["state"]

    if status != "ALLOW":
        return model

    if state == "MA20_CHOP_ZONE":
        model["status"] = "WATCH"
        model["status_text"] = "👀【观察接近】"
        model["trigger"] = model["trigger"] + "；但价格处于 MA20 纠缠区，等待确认K"
        model["allow_action"] = "等待连续2根15m确认K后再出手"
        model["risk"] = "MA20 附近来回穿越，容易假突破/假跌破"
        return model

    if direction == "LONG" and state in ["CONFIRMED_BELOW", "SINGLE_BELOW", "FALSE_BREAKOUT"]:
        model["status"] = "WATCH"
        model["status_text"] = "👀【观察接近】"
        model["trigger"] = model["trigger"] + "；但 MA20 尚未有效站回"
        model["allow_action"] = "等待连续2根15m收在 MA20 上方，再考虑多头"
        model["risk"] = "多头信号未通过 MA20 确认K过滤"
        return model

    if direction == "SHORT" and state in ["CONFIRMED_ABOVE", "SINGLE_ABOVE", "FALSE_BREAKDOWN"]:
        model["status"] = "WATCH"
        model["status_text"] = "👀【观察接近】"
        model["trigger"] = model["trigger"] + "；但 MA20 尚未有效跌破"
        model["allow_action"] = "等待连续2根15m收在 MA20 下方，再考虑空头"
        model["risk"] = "空头信号未通过 MA20 确认K过滤"
        return model

    return model


def build_execution_plan(symbol, model, df):
    """
    V8 执行单：
    只有 ALLOW 才给 Entry / SL / Invalid / Position。
    WATCH / BLOCK 只给观察条件。
    """
    last = df.iloc[-2]

    price = last["close"]
    high = last["high"]
    low = last["low"]
    ma20 = last["ma20"]
    direction = model["direction"]
    status = model["status"]

    if status != "ALLOW":
        return (
            "执行单：\n"
            "状态：未触发执行单\n"
            "原因：当前不是 ✅【允许出手】\n"
            f"观察：{model.get('trigger', '等待新结构')}\n"
        )

    if direction == "LONG":
        entry_1 = price
        entry_2 = ma20
        stop_loss = min(low, ma20) * 0.998
        invalid_price = ma20 * 0.997
        risk = entry_1 - stop_loss

        if risk <= 0:
            take_profit_1 = entry_1 * 1.003
            take_profit_2 = entry_1 * 1.006
        else:
            take_profit_1 = entry_1 + risk
            take_profit_2 = entry_1 + risk * 2

        return f"""执行单：
方向：LONG
入场1：{entry_1:.2f}
入场2：{entry_2:.2f}（回踩 MA20 不破）
止损：{stop_loss:.2f}
无效价：{invalid_price:.2f}
止盈1：{take_profit_1:.2f}
止盈2：{take_profit_2:.2f}
仓位：试仓 20%，确认后最多 40%
管理：浮盈 1R 后止损推保本；跌破无效价立刻撤销多头计划
"""

    if direction == "SHORT":
        entry_1 = price
        entry_2 = ma20
        stop_loss = max(high, ma20) * 1.002
        invalid_price = ma20 * 1.003
        risk = stop_loss - entry_1

        if risk <= 0:
            take_profit_1 = entry_1 * 0.997
            take_profit_2 = entry_1 * 0.994
        else:
            take_profit_1 = entry_1 - risk
            take_profit_2 = entry_1 - risk * 2

        return f"""执行单：
方向：SHORT
入场1：{entry_1:.2f}
入场2：{entry_2:.2f}（反抽 MA20 不上）
止损：{stop_loss:.2f}
无效价：{invalid_price:.2f}
止盈1：{take_profit_1:.2f}
止盈2：{take_profit_2:.2f}
仓位：试仓 20%，确认后最多 40%
管理：浮盈 1R 后止损推保本；站回无效价立刻撤销空头计划
"""

    return (
        "执行单：\n"
        "状态：无方向，不生成执行单\n"
    )


def should_push_to_dingtalk(model):
    # V3 只是前置结构：先定义未来钉钉是否推送
    # 当前规则：只有 ALLOW 才值得钉钉强提醒
    return model["status"] == "ALLOW"


def main():
    load_env()

    print()
    print("BTC/ETH 看盘引擎 V8.1 启动")
    print(f"北京时间：{now_beijing()}")
    print("规则：15m 找入场，MA20区域确认，BTC领航，1H/4H过滤，资金四确认，并输出执行单")
    print("推送规则：只有 ✅【允许出手】 且通过 BTC领航 + 1H/4H + 资金三确认，才推送钉钉")

    market_results = {}
    push_queue = []

    for symbol in SYMBOLS:
        try:
            df = fetch_ohlcv(symbol)
            df = add_indicators(df)
            model = detect_model(df)
            htf_bias = detect_htf_bias(symbol)

            market_results[symbol] = {
                "df": df,
                "model": model,
                "htf_bias": htf_bias
            }

        except Exception as e:
            print(f"{symbol} 获取失败：{e}")

    btc_symbol = "BTC/USDT:USDT"
    btc_model = market_results.get(btc_symbol, {}).get("model")

    if btc_model:
        btc_leader = get_btc_leader_bias(btc_model)
    else:
        btc_leader = {
            "bias": "WAIT",
            "text": "BTC 数据缺失，所有 ETH 信号降级观察"
        }

    print()
    print("==============================")
    print("BTC 领航判断")
    print(f"领航方向：{btc_leader['bias']}")
    print(f"领航解释：{btc_leader['text']}")
    print("==============================")

    for symbol, result in market_results.items():
        df = result["df"]
        model = result["model"]
        htf_bias = result["htf_bias"]

        model = apply_btc_leader_filter(symbol, model, btc_leader)
        model = apply_htf_filter(symbol, model, htf_bias)
        model = apply_flow_filter(symbol, model, df)
        model = apply_ma20_zone_filter(symbol, model, df)

        card = build_signal_card(symbol, df, model)

        print()
        print("==============================")
        print(card)
        print("==============================")

        if should_push_to_dingtalk(model):
            push_queue.append(card)

    print()
    print("钉钉推送前置检查：")

    if push_queue:
        print(f"本轮共有 {len(push_queue)} 条允许出手信号，正在推送钉钉...")

        for card in push_queue:
            try:
                send_dingtalk_markdown("BTC/ETH 允许出手信号", card)
                print("钉钉推送成功")
            except Exception as e:
                print(f"钉钉推送失败：{e}")
    else:
        print("本轮没有 ✅【允许出手】 信号，不推送钉钉。")


if __name__ == "__main__":
    main()
