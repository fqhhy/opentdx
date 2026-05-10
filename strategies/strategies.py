"""
量化策略实现 — 均使用向量化计算，无未来函数。
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def sma_cross(close: pd.Series, fast: int = 5, slow: int = 20) -> pd.Series:
    """双均线交叉 — 快线上穿慢线买入，下穿卖出。

    Parameters
    ----------
    close : Series
        收盘价序列
    fast : int
        快线周期
    slow : int
        慢线周期

    Returns
    -------
    Series
        信号: 1=买入, -1=卖出, 0=无操作
    """
    ma_fast = close.rolling(fast).mean()
    ma_slow = close.rolling(slow).mean()

    signals = pd.Series(0, index=close.index)
    # 金叉: 快线从下方上穿慢线
    cross_up = (ma_fast > ma_slow) & (ma_fast.shift(1) <= ma_slow.shift(1))
    # 死叉: 快线从上方下穿慢线
    cross_down = (ma_fast < ma_slow) & (ma_fast.shift(1) >= ma_slow.shift(1))

    signals[cross_up] = 1
    signals[cross_down] = -1
    return signals


def macd_signal(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.Series:
    """MACD 金叉死叉 — DIF 上穿 DEA 买入，下穿卖出。

    Parameters
    ----------
    close : Series
        收盘价
    fast, slow, signal : int
        MACD 参数

    Returns
    -------
    Series
        信号: 1=买入, -1=卖出, 0=无操作
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_bar = 2 * (dif - dea)

    signals = pd.Series(0, index=close.index)
    signals[(dif > dea) & (dif.shift(1) <= dea.shift(1))] = 1
    signals[(dif < dea) & (dif.shift(1) >= dea.shift(1))] = -1

    # 附加指标列（非信号）
    signals.attrs['dif'] = dif
    signals.attrs['dea'] = dea
    signals.attrs['macd'] = macd_bar
    return signals


def bollinger_break(
    close: pd.Series,
    period: int = 20,
    std: float = 2.0,
) -> pd.Series:
    """布林带突破 — 价格下穿上轨卖出，上穿下轨买入。

    Parameters
    ----------
    close : Series
        收盘价
    period : int
        均线周期
    std : float
        标准差倍数

    Returns
    -------
    Series
        信号
    """
    ma = close.rolling(period).mean()
    std_dev = close.rolling(period).std()
    upper = ma + std * std_dev
    lower = ma - std * std_dev

    signals = pd.Series(0, index=close.index)
    # 突破下轨 → 买
    signals[(close < lower) & (close.shift(1) >= lower.shift(1))] = 1
    # 突破上轨 → 卖
    signals[(close > upper) & (close.shift(1) <= upper.shift(1))] = -1
    return signals


def rsi_mean_reversion(
    close: pd.Series,
    period: int = 14,
    oversold: float = 30,
    overbought: float = 70,
) -> pd.Series:
    """RSI 超买超卖 — RSI 从超卖区回升买入，从超买区回落卖出。

    Parameters
    ----------
    close : Series
        收盘价
    period : int
        RSI 周期
    oversold : float
        超卖阈值
    overbought : float
        超买阈值

    Returns
    -------
    Series
        信号
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    signals = pd.Series(0, index=close.index)
    # RSI 从超卖区向上穿越 → 买
    signals[(rsi > oversold) & (rsi.shift(1) <= oversold)] = 1
    # RSI 从超买区向下穿越 → 卖
    signals[(rsi < overbought) & (rsi.shift(1) >= overbought)] = -1

    signals.attrs['rsi'] = rsi
    return signals


def turtle_channel(
    high: pd.Series, low: pd.Series, close: pd.Series,
    entry_period: int = 20, exit_period: int = 10,
) -> pd.Series:
    """海龟通道突破 — Donchian Channel。

    Parameters
    ----------
    high, low, close : Series
        OHLC 数据
    entry_period : int
        入场通道周期
    exit_period : int
        离场通道周期

    Returns
    -------
    Series
        信号
    """
    entry_high = high.rolling(entry_period).max()
    entry_low = low.rolling(entry_period).min()
    exit_high = high.rolling(exit_period).max()
    exit_low = low.rolling(exit_period).min()

    signals = pd.Series(0, index=close.index)
    # 价格突破 entry 通道高点 → 买
    signals[close > entry_high.shift(1)] = 1
    # 价格跌破 exit 通道低点 → 卖
    signals[close < exit_low.shift(1)] = -1
    return signals


def volume_price_divergence(
    close: pd.Series, volume: pd.Series,
    period: int = 20,
) -> pd.Series:
    """量价背离 — 价涨量缩卖出，价跌量增买入。

    Parameters
    ----------
    close : Series
        收盘价
    volume : Series
        成交量
    period : int
        判断周期

    Returns
    -------
    Series
        信号
    """
    price_chg = close.pct_change(period)
    vol_chg = volume.pct_change(period)

    signals = pd.Series(0, index=close.index)
    # 价跌量增 → 吸筹信号，买入
    signals[(price_chg < 0) & (vol_chg > 0.3)] = 1
    # 价涨量缩 → 出货信号，卖出
    signals[(price_chg > 0.05) & (vol_chg < -0.2)] = -1
    return signals
