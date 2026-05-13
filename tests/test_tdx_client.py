from datetime import date

from opentdx.const import (
    ADJUST,
    BLOCK_FILE_TYPE,
    CATEGORY,
    EX_MARKET,
    MARKET,
    PERIOD,
    SORT_TYPE,
)


class TestTdxClientStock:
    """TdxClient A股相关 API"""

    def test_stock_count(self, tdx):
        result = tdx.stock_count(MARKET.SZ)
        assert isinstance(result, int)
        assert result > 1000

    def test_stock_list(self, tdx):
        result = tdx.stock_list(MARKET.SZ, start=0, count=5)
        assert isinstance(result, list)
        assert len(result) == 5
        for item in result:
            assert 'code' in item and 'name' in item
            assert len(item['code']) == 6

    def test_stock_kline(self, tdx):
        result = tdx.stock_kline(MARKET.SZ, '000001', PERIOD.DAILY, count=10)
        assert isinstance(result, list)
        assert len(result) == 10
        for k in result:
            assert 'datetime' in k and 'open' in k and 'high' in k and 'low' in k and 'close' in k
            assert k['high'] >= k['low']
            assert k['open'] >= 0 and k['close'] >= 0

    def test_stock_kline_with_adjust(self, tdx):
        qfq = tdx.stock_kline(MARKET.SZ, '000001', PERIOD.DAILY, count=5, adjust=ADJUST.QFQ)
        hfq = tdx.stock_kline(MARKET.SZ, '000001', PERIOD.DAILY, count=5, adjust=ADJUST.HFQ)
        no_adj = tdx.stock_kline(MARKET.SZ, '000001', PERIOD.DAILY, count=5, adjust=ADJUST.NONE)
        assert len(qfq) == len(no_adj)
        # QFQ 和 HFQ 价格应该不同（对于有分红/送股的股票）
        assert qfq[-1]['close'] != hfq[-1]['close'] or qfq[-1]['open'] != hfq[-1]['open']

    def test_stock_quotes(self, tdx):
        result = tdx.stock_quotes(MARKET.SZ, '000001')
        assert isinstance(result, list)
        assert len(result) == 1
        q = result[0]
        assert q['code'] == '000001'
        assert q['market'] == MARKET.SZ
        assert q['pre_close'] > 0
        assert q['high'] >= q['low']

    def test_stock_quotes_multi(self, tdx):
        result = tdx.stock_quotes([(MARKET.SZ, '000001'), (MARKET.SH, '600000')])
        assert isinstance(result, list)
        assert len(result) == 2
        for q in result:
            assert q['pre_close'] > 0
            assert q['high'] >= q['low']

    def test_stock_quotes_list(self, tdx):
        result = tdx.stock_quotes_list(CATEGORY.A, count=5)
        assert isinstance(result, list)
        assert len(result) == 5
        for q in result:
            assert 'code' in q and q['pre_close'] > 0

    def test_stock_quotes_list_with_sort(self, tdx):
        result = tdx.stock_quotes_list(CATEGORY.A, count=5, sort_type=SORT_TYPE.TOTAL_AMOUNT)
        assert isinstance(result, list)
        assert len(result) == 5
        # 排序后 amount 应为降序
        amounts = [q.get('amount', 0) for q in result]
        assert amounts == sorted(amounts, reverse=True), f"应按成交额降序: {amounts}"

    def test_stock_top_board(self, tdx):
        result = tdx.stock_top_board(CATEGORY.A)
        assert isinstance(result, dict)
        assert len(result) > 0
        for key, board in result.items():
            assert isinstance(board, list)
            if board:
                assert 'code' in board[0] and 'price' in board[0]

    def test_stock_quotes_detail(self, tdx):
        result = tdx.stock_quotes_detail(MARKET.SZ, '000001')
        assert isinstance(result, list)
        assert len(result) == 1
        d = result[0]
        assert 'handicap' in d
        assert d['pre_close'] > 0

    def test_stock_quotes_detail_multi(self, tdx):
        result = tdx.stock_quotes_detail([(MARKET.SZ, '000001'), (MARKET.SH, '600000')])
        assert isinstance(result, list)
        assert len(result) == 2

    def test_index_info(self, tdx):
        result = tdx.index_info([(MARKET.SH, '999999'), (MARKET.SZ, '399001')])
        assert isinstance(result, list)
        assert len(result) == 2
        for idx in result:
            assert 'code' in idx
            assert idx['open'] >= 0 and idx['high'] >= idx['low']

    def test_index_momentum(self, tdx):
        result = tdx.index_momentum(MARKET.SH, '999999')
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], int)

    def test_stock_tick_chart(self, tdx):
        result = tdx.stock_tick_chart(MARKET.SH, '999999')
        assert isinstance(result, list)
        if result:
            assert 'time' in result[0] and 'price' in result[0]

    def test_stock_transaction(self, tdx):
        result = tdx.stock_transaction(MARKET.SZ, '000001')
        assert isinstance(result, list)
        if result:
            assert 'price' in result[0] and result[0]['price'] > 0

    def test_stock_transaction_history(self, tdx):
        result = tdx.stock_transaction(MARKET.SZ, '000001', date(2026, 4, 10))
        assert isinstance(result, list)
        if result:
            assert 'price' in result[0] and result[0]['price'] > 0

    def test_stock_unusual(self, tdx):
        result = tdx.stock_unusual(MARKET.SZ)
        assert isinstance(result, list)
        if result:
            assert 'index' in result[0] and 'code' in result[0]

    def test_stock_f10(self, tdx):
        result = tdx.stock_f10(MARKET.SZ, '000001')
        assert isinstance(result, list)
        assert len(result) > 0
        assert 'name' in result[0] and result[0]['name']

    def test_stock_vol_profile(self, tdx):
        result = tdx.stock_vol_profile(MARKET.SZ, '000001')
        assert result is None or isinstance(result, list)

    def test_stock_chart_sampling(self, tdx):
        result = tdx.stock_chart_sampling(MARKET.SZ, '000001')
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], float)

    def test_stock_block(self, tdx):
        result = tdx.stock_block(BLOCK_FILE_TYPE.DEFAULT)
        assert result is not None
        assert isinstance(result, list)
        if result:
            assert 'code' in result[0] and 'blockname' in result[0]


    def test_stock_auction(self, tdx):
        result = tdx.stock_auction(MARKET.SZ, '000001')
        assert isinstance(result, list)
        if not result:
            return
        item = result[0]
        assert 'time' in item and 'price' in item
        assert 'matched' in item and 'unmatched' in item
        assert isinstance(item['unmatched'], int)

    def test_stock_history_orders(self, tdx):
        result = tdx.stock_history_orders(MARKET.SZ, '000001', date(2026, 5, 8))
        assert isinstance(result, list)
        if result:
            assert 'price' in result[0] and 'vol' in result[0]

    def test_stock_kline_with_times(self, tdx):
        result = tdx.stock_kline(MARKET.SH, '999999', PERIOD.MINS, times=10, count=10)
        assert isinstance(result, list)
        assert len(result) == 10
        for k in result:
            assert 'datetime' in k and 'open' in k
            assert k['high'] >= k['low']

    def test_stock_quotes_detail_tuple(self, tdx):
        result = tdx.stock_quotes_detail((MARKET.SZ, '000001'))
        assert result is None or isinstance(result, list)

    def test_index_info_single(self, tdx):
        result = tdx.index_info(MARKET.SH, '999999')
        assert isinstance(result, list)
        assert len(result) > 0

    def test_index_info_tuple(self, tdx):
        result = tdx.index_info((MARKET.SH, '999999'))
        assert result is None or isinstance(result, list)


class TestTdxClientGoods:
    """TdxClient 扩展行情 API"""

    def test_goods_count(self, tdx):
        result = tdx.goods_count()
        assert isinstance(result, int)
        assert result > 1000

    def test_goods_category_list(self, tdx):
        result = tdx.goods_category_list()
        assert isinstance(result, list)
        assert len(result) > 0
        for item in result:
            assert 'name' in item and 'code' in item and 'abbr' in item

    def test_goods_list(self, tdx):
        result = tdx.goods_list(start=0, count=5)
        assert isinstance(result, list)
        assert len(result) == 5
        for item in result:
            assert 'code' in item and 'name' in item

    def test_goods_quotes(self, tdx):
        result = tdx.goods_quotes(EX_MARKET.US_STOCK, 'TSLA')
        if result is None:
            return
        assert isinstance(result, list)
        assert len(result) == 1
        q = result[0]
        assert q['code'] == 'TSLA'
        assert q['pre_close'] > 0

    def test_goods_quotes_multi(self, tdx):
        result = tdx.goods_quotes([(EX_MARKET.US_STOCK, 'TSLA'), (EX_MARKET.HK_MAIN_BOARD, '09988')])
        if result is None:
            return
        assert isinstance(result, list)
        assert len(result) == 2
        for q in result:
            assert q['pre_close'] >= 0

    def test_goods_kline(self, tdx):
        result = tdx.goods_kline(EX_MARKET.US_STOCK, 'TSLA', PERIOD.DAILY, count=5)
        assert isinstance(result, list)
        assert len(result) == 5
        for k in result:
            assert 'datetime' in k and 'open' in k and 'close' in k
            assert k['high'] >= k['low']
            assert k['open'] > 0

    def test_goods_tick_chart(self, tdx):
        result = tdx.goods_tick_chart(EX_MARKET.US_STOCK, 'TSLA')
        assert isinstance(result, list)
        if result:
            assert 'time' in result[0] and 'price' in result[0]

    def test_goods_chart_sampling(self, tdx):
        result = tdx.goods_chart_sampling(EX_MARKET.US_STOCK, 'TSLA')
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], float)

    def test_goods_quotes_list(self, tdx):
        result = tdx.goods_quotes_list(EX_MARKET.US_STOCK, count=5)
        if result is None:
            return
        assert isinstance(result, list)
        assert len(result) == 5
        for q in result:
            assert 'code' in q

    def test_goods_quotes_list_with_sort(self, tdx):
        result = tdx.goods_quotes_list(EX_MARKET.HK_MAIN_BOARD, count=5, sortType=SORT_TYPE.TOTAL_AMOUNT)
        if result is None:
            return
        assert isinstance(result, list)
        assert len(result) == 5
        amounts = [q.get('amount', 0) for q in result]
        assert amounts == sorted(amounts, reverse=True)

    def test_goods_history_transaction(self, tdx):
        result = tdx.goods_history_transaction(EX_MARKET.US_STOCK, 'TSLA', date(2026, 5, 1))
        assert isinstance(result, list)
        if result:
            assert 'time' in result[0] and 'price' in result[0] and 'bs_flag' in result[0]
            assert result[0]['price'] > 0

    def test_goods_tick_chart_with_date(self, tdx):
        result = tdx.goods_tick_chart(EX_MARKET.US_STOCK, 'TSLA', date(2026, 5, 1))
        assert isinstance(result, list)

    def test_goods_kline_with_period(self, tdx):
        result = tdx.goods_kline(EX_MARKET.HK_MAIN_BOARD, '09988', PERIOD.DAILY, count=5)
        assert isinstance(result, list)
        assert len(result) == 5
        for k in result:
            assert k['high'] >= k['low']
