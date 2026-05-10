"""
轻量回测引擎 — 基于 pandas 向量化计算，无 look-ahead bias。
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass, field


@dataclass
class BacktestResult:
    total_return: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    equity_curve: pd.Series = field(default_factory=pd.Series)
    trades: list[dict] = field(default_factory=list)


class BacktestEngine:
    """向量化回测引擎。

    Parameters
    ----------
    initial_capital : float
        初始资金
    commission : float
        手续费率（双向），默认 0.0003 (万三)
    slippage : float
        滑点比例，默认 0.001 (千一)
    """

    def __init__(
        self,
        initial_capital: float = 100_000,
        commission: float = 0.0003,
        slippage: float = 0.001,
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

    def run(self, df: pd.DataFrame, signals: pd.Series) -> BacktestResult:
        """执行回测。

        Parameters
        ----------
        df : DataFrame
            需包含 'close' 列，索引为日期。
        signals : Series
            交易信号，与 df 等长。1=买入, -1=卖出, 0=无操作。

        Returns
        -------
        BacktestResult
        """
        if len(df) < 2:
            return BacktestResult()

        df = df.copy()
        # 过滤无效价格
        df = df[df['close'].notna() & (df['close'] > 0)]
        if len(df) < 2:
            return BacktestResult()

        df['signal'] = signals.loc[df.index].values

        # 执行价 = close * (1 + slippage * 方向)
        df['exec_price'] = np.where(
            df['signal'] == 1, df['close'] * (1 + self.slippage),
            np.where(df['signal'] == -1, df['close'] * (1 - self.slippage),
                     df['close'])
        )

        # 状态变量
        position = 0.0       # 持仓股数
        cash = self.initial_capital
        equity = np.zeros(len(df))
        trade_records = []

        for i in range(len(df)):
            sig = df['signal'].iloc[i]
            price = df['exec_price'].iloc[i]
            if price <= 0:
                equity[i] = cash + position * df['close'].iloc[i]
                continue

            if sig == 1 and position == 0:
                # 买入：全仓
                position = cash * (1 - self.commission) / price
                cash = 0
                trade_records.append({
                    'date': df.index[i], 'action': 'buy', 'price': price,
                    'shares': position,
                })
            elif sig == -1 and position > 0:
                # 卖出
                cash = position * price * (1 - self.commission)
                trade_records.append({
                    'date': df.index[i], 'action': 'sell', 'price': price,
                    'shares': position, 'pnl': cash - self.initial_capital,
                })
                position = 0

            equity[i] = cash + position * df['close'].iloc[i]

        # 强制平仓
        if position > 0:
            equity[-1] = position * df['close'].iloc[-1] * (1 - self.commission)

        equity_series = pd.Series(equity, index=df.index)
        return self._calc_metrics(equity_series, trade_records)

    def _calc_metrics(self, equity: pd.Series, trades: list[dict]) -> BacktestResult:
        result = BacktestResult(equity_curve=equity, trades=trades)

        if len(equity) < 2:
            return result

        result.total_return = (equity.iloc[-1] / self.initial_capital - 1) * 100

        # 年化收益率
        days = (equity.index[-1] - equity.index[0]).days
        if days > 0 and equity.iloc[-1] > 0:
            result.annual_return = (
                (equity.iloc[-1] / self.initial_capital) ** (365 / days) - 1
            ) * 100

        # 最大回撤
        peak = equity.expanding().max()
        drawdown = (equity - peak) / peak * 100
        result.max_drawdown = abs(drawdown.min())

        # 夏普比率
        daily_ret = equity.pct_change().dropna()
        if len(daily_ret) > 1 and daily_ret.std() > 0:
            result.sharpe_ratio = (
                daily_ret.mean() / daily_ret.std() * np.sqrt(252)
            )

        # 胜率
        sell_trades = [t for t in trades if t['action'] == 'sell']
        if sell_trades:
            wins = sum(1 for t in sell_trades if t.get('pnl', 0) > 0)
            result.win_rate = wins / len(sell_trades) * 100
        result.total_trades = len(sell_trades)

        return result


def run_backtest(
    engine: BacktestEngine, df: pd.DataFrame, signals: pd.Series,
) -> BacktestResult:
    return engine.run(df, signals)
