#!/usr/bin/env python
"""
真实数据策略回测 — 拉取通达信K线数据，多策略对比回测。
"""
from __future__ import annotations

import sys
from datetime import date

import pandas as pd
import numpy as np

from opentdx import TdxClient, MARKET, PERIOD, ADJUST
from strategies.backtest_engine import BacktestEngine, BacktestResult
from strategies.strategies import (
    sma_cross, macd_signal, bollinger_break,
    rsi_mean_reversion, turtle_channel,
)

STOCKS = [
    (MARKET.SZ, '000001', '平安银行'),
    (MARKET.SH, '600519', '贵州茅台'),
    (MARKET.SZ, '000858', '五粮液'),
    (MARKET.SH, '600036', '招商银行'),
    (MARKET.SZ, '300750', '宁德时代'),
    (MARKET.SH, '601318', '中国平安'),
    (MARKET.SZ, '002415', '海康威视'),
    (MARKET.SH, '600276', '恒瑞医药'),
]


def fetch_kline(market: MARKET, code: str, count: int = 2500) -> pd.DataFrame:
    """拉取K线数据并转为 DataFrame。"""
    with TdxClient() as c:
        bars = c.stock_kline(market, code, PERIOD.DAILY, count=count, adjust=ADJUST.HFQ)
    if not bars:
        raise RuntimeError(f"未获取到 {code} 的K线数据")

    df = pd.DataFrame(bars)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime').sort_index()
    # 去掉上市初期无量数据
    df = df[df['vol'] > 0]
    return df


def print_result(name: str, res: BacktestResult, stock_name: str = ''):
    """格式化打印回测结果。"""
    tag = f" {stock_name}" if stock_name else ""
    print(f"\n{'='*60}")
    print(f"  {name}{tag}")
    print(f"{'='*60}")
    print(f"  累计收益:   {res.total_return:>8.2f}%")
    print(f"  年化收益:   {res.annual_return:>8.2f}%")
    print(f"  最大回撤:   {res.max_drawdown:>8.2f}%")
    print(f"  夏普比率:   {res.sharpe_ratio:>8.2f}")
    print(f"  胜率:       {res.win_rate:>8.1f}%")
    print(f"  交易次数:   {res.total_trades:>8}")


def run_single_stock(df: pd.DataFrame, engine: BacktestEngine):
    """单只股票多策略对比。"""
    close = df['close']
    high = df.get('high', close)
    low = df.get('low', close)
    vol = df.get('vol', pd.Series(1, index=df.index))

    strategies = {
        '双均线(5,20)': sma_cross(close, 5, 20),
        '双均线(10,60)': sma_cross(close, 10, 60),
        'MACD(12,26,9)': macd_signal(close, 12, 26, 9),
        '布林带(20,2)': bollinger_break(close, 20, 2.0),
        'RSI(14)': rsi_mean_reversion(close, 14, 30, 70),
        '海龟通道(20,10)': turtle_channel(high, low, close, 20, 10),
    }

    for name, sig in strategies.items():
        res = engine.run(df, sig)
        print_result(name, res)


def run_multi_stock(engine: BacktestEngine):
    """多只股票 × 多策略对比。"""
    results = []
    for market, code, sname in STOCKS:
        try:
            df = fetch_kline(market, code, count=2500)
        except Exception as e:
            print(f"  [跳过] {code} {sname}: {e}")
            continue

        close = df['close']
        high = df.get('high', close)
        low = df.get('low', close)

        strategies = {
            '双均线(5,20)': sma_cross(close, 5, 20),
            'MACD(12,26,9)': macd_signal(close, 12, 26, 9),
            '布林带(20,2)': bollinger_break(close, 20, 2.0),
            '海龟通道(20,10)': turtle_channel(high, low, close, 20, 10),
        }

        for sname_strat, sig in strategies.items():
            res = engine.run(df, sig)
            results.append({
                '股票': f'{code} {sname}',
                '策略': sname_strat,
                '累计收益%': round(res.total_return, 2),
                '年化收益%': round(res.annual_return, 2),
                '最大回撤%': round(res.max_drawdown, 2),
                '夏普比率': round(res.sharpe_ratio, 2),
                '胜率%': round(res.win_rate, 1),
                '交易次数': res.total_trades,
            })

    return pd.DataFrame(results)


def run_sector_rotation():
    """板块轮动策略 — 基于行业板块成分股强弱轮动。

    思路: 每日计算各板块成分股的涨幅中位数，选最强板块持有。
    """
    from opentdx import BOARD_TYPE

    print(f"\n{'='*60}")
    print(f"  板块轮动策略")
    print(f"{'='*60}")

    with TdxClient() as c:
        # 获取行业板块列表
        boards = c.q_client().get_board_list(BOARD_TYPE.HY, count=200)
        if not boards:
            print("  未获取到板块列表")
            return

        print(f"  获取到 {len(boards)} 个行业板块")

        # 取前 20 个板块的成分股行情，计算板块强度
        board_scores = []
        for b in boards[:30]:
            try:
                members = c.q_client().get_board_members_quotes(
                    b['code'], count=100,
                )
                if not members or len(members) < 3:
                    continue

                # 板块强度 = 涨跌幅中位数
                changes = [
                    m.get('change_pct', 0) for m in members
                    if m.get('change_pct') is not None
                ]
                if changes:
                    median_chg = np.median(changes)
                    board_scores.append({
                        '板块代码': b['code'],
                        '板块名称': b.get('name', b['code']),
                        '成分股数': len(members),
                        '涨跌幅中位数%': round(median_chg, 2),
                    })
            except Exception:
                continue

        if board_scores:
            df = pd.DataFrame(board_scores).sort_values(
                '涨跌幅中位数%', ascending=False,
            )
            print(f"\n  {'板块代码':<10} {'板块名称':<12} {'成分股数':<8} {'涨跌幅中位%':<10}")
            print(f"  {'-'*45}")
            for _, row in df.head(15).iterrows():
                chg = row['涨跌幅中位数%']
                tag = '↑' if chg > 0 else '↓'
                print(
                    f"  {row['板块代码']:<10} {row['板块名称']:<12} "
                    f"{row['成分股数']:<8} {tag}{abs(chg):.2f}%"
                )


def main():
    print("=" * 60)
    print("  OpenTDX 量化策略回测系统")
    print("=" * 60)

    engine = BacktestEngine(initial_capital=100_000)

    # ---- 单只股票多策略对比 ----
    print("\n\n>>> 一、平安银行 (000001.SZ) 多策略对比")
    try:
        df_pa = fetch_kline(MARKET.SZ, '000001', count=2500)
        print(f"  数据: {df_pa.index[0].date()} ~ {df_pa.index[-1].date()}, "
              f"共 {len(df_pa)} 条")
        run_single_stock(df_pa, engine)
    except Exception as e:
        print(f"  错误: {e}")

    # ---- 贵州茅台单策略 ----
    print("\n\n>>> 二、贵州茅台 (600519.SH) 多策略对比")
    try:
        df_mt = fetch_kline(MARKET.SH, '600519', count=2500)
        print(f"  数据: {df_mt.index[0].date()} ~ {df_mt.index[-1].date()}, "
              f"共 {len(df_mt)} 条")
        run_single_stock(df_mt, engine)
    except Exception as e:
        print(f"  错误: {e}")

    # ---- 多股票多策略对比 ----
    print("\n\n>>> 三、多股票 × 多策略 综合对比")
    df_result = run_multi_stock(engine)
    if not df_result.empty:
        # 按累计收益排序
        print("\n  综合排名 (按累计收益):")
        ranked = df_result.sort_values('累计收益%', ascending=False)
        print(ranked.to_string(index=False))

        # 策略统计
        print("\n  策略均值统计:")
        stats = df_result.groupby('策略').agg({
            '累计收益%': 'mean', '年化收益%': 'mean',
            '最大回撤%': 'mean', '夏普比率': 'mean', '胜率%': 'mean',
        }).round(2)
        print(stats.to_string())

    # ---- 板块轮动 ----
    print("\n\n>>> 四、板块强度扫描")
    run_sector_rotation()

    print(f"\n{'='*60}")
    print("  回测完成")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
