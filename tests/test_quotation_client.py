from datetime import date

from opentdx.const import (
    BLOCK_FILE_TYPE,
    CATEGORY,
    MARKET,
    PERIOD,
)


class TestQuotationClientLogin:
    """登录和心跳"""

    def test_connected(self, qc):
        assert qc.connected is True

    def test_heartbeat(self, qc):
        result = qc._do_heartbeat()
        assert result is not None


class TestQuotationClientStock:
    """A 股行情 API"""

    def test_get_count(self, qc):
        result = qc.get_count(MARKET.SZ)
        assert isinstance(result, int)
        assert result > 1000  # 深市股票数应远大于1000

    def test_get_count_sh(self, qc):
        result = qc.get_count(MARKET.SH)
        assert isinstance(result, int)
        assert result > 1000  # 沪市股票数应远大于1000

    def test_get_list(self, qc):
        result = qc.get_list(MARKET.SZ, start=0, count=5)
        assert isinstance(result, list)
        assert len(result) == 5
        for item in result:
            assert 'code' in item and 'name' in item
            assert len(item['code']) == 6
            assert isinstance(item['name'], str) and len(item['name']) > 0

    def test_get_kline(self, qc):
        result = qc.get_kline(MARKET.SZ, '000001', PERIOD.DAILY, count=10)
        assert isinstance(result, list)
        assert len(result) == 10
        for k in result:
            assert 'datetime' in k and 'open' in k and 'high' in k and 'low' in k and 'close' in k
            assert k['open'] >= 0 and k['high'] >= 0 and k['low'] >= 0 and k['close'] >= 0
            assert k['high'] >= k['low']

    def test_get_quotes(self, qc):
        result = qc.get_quotes(MARKET.SZ, '000001')
        assert isinstance(result, list)
        assert len(result) == 1
        q = result[0]
        assert q['code'] == '000001'
        assert q['market'] == MARKET.SZ
        assert q['pre_close'] > 0
        assert q['open'] >= 0
        assert q['high'] >= q['low']

    def test_get_quotes_multi(self, qc):
        result = qc.get_quotes([(MARKET.SZ, '000001'), (MARKET.SH, '600000')])
        assert isinstance(result, list)
        assert len(result) == 2
        for q in result:
            assert 'code' in q and 'market' in q
            assert q['pre_close'] > 0
            assert q['high'] >= q['low']

    def test_get_stock_quotes_details(self, qc):
        result = qc.get_stock_quotes_details(MARKET.SZ, '000001')
        assert isinstance(result, list)
        assert len(result) == 1
        d = result[0]
        assert d['code'] == '000001'
        assert 'handicap' in d
        assert d['pre_close'] > 0
        assert d['high'] >= d['low']
        h = d['handicap']
        assert isinstance(h, dict)
        assert 'bid' in h and 'ask' in h
        if h['bid'] and h['ask']:
            assert h['bid'][0]['price'] <= h['ask'][0]['price']

    def test_get_stock_quotes_details_multi(self, qc):
        result = qc.get_stock_quotes_details([(MARKET.SZ, '000001'), (MARKET.SH, '600000')])
        assert isinstance(result, list)
        assert len(result) == 2
        for d in result:
            assert d['pre_close'] > 0
            assert d['high'] >= d['low']

    def test_get_stock_top_board(self, qc):
        result = qc.get_stock_top_board(CATEGORY.A)
        assert isinstance(result, dict)
        assert len(result) > 0
        for board in result.values():
            assert isinstance(board, list)
            if board:
                assert 'code' in board[0]

    def test_get_stock_quotes_list(self, qc):
        result = qc.get_stock_quotes_list(CATEGORY.A, count=5)
        assert isinstance(result, list)
        assert len(result) == 5
        for q in result:
            assert 'code' in q and 'market' in q
            assert q['pre_close'] > 0

    def test_get_stock_quotes_list_all(self, qc):
        result = qc.get_stock_quotes_list(CATEGORY.A, count=0)
        assert isinstance(result, list)
        assert len(result) > 0
        for q in result:
            assert 'code' in q and q['pre_close'] >= 0

    def test_get_tick_chart(self, qc):
        result = qc.get_tick_chart(MARKET.SH, '999999')
        assert isinstance(result, list)
        if result:
            assert 'price' in result[0]

    def test_get_transaction(self, qc):
        result = qc.get_transaction(MARKET.SZ, '000001')
        assert isinstance(result, list)
        if result:
            tx = result[0]
            assert 'time' in tx and 'price' in tx and 'vol' in tx
            assert tx['price'] > 0

    def test_get_transaction_history(self, qc):
        result = qc.get_transaction(MARKET.SZ, '000001', date(2026, 4, 10))
        assert isinstance(result, list)
        if result:
            assert 'price' in result[0] and result[0]['price'] > 0

    def test_get_company_info(self, qc):
        result = qc.get_company_info(MARKET.SZ, '000001')
        assert isinstance(result, list)
        assert len(result) > 0
        assert 'name' in result[0] and result[0]['name']

    def test_get_auction(self, qc):
        result = qc.get_auction(MARKET.SZ, '300308')
        assert isinstance(result, list)
        if result:
            item = result[0]
            for key in ('time', 'price', 'matched', 'unmatched'):
                assert key in item

    def test_get_unusual(self, qc):
        result = qc.get_unusual(MARKET.SZ)
        assert isinstance(result, list)
        if result:
            item = result[0]
            assert 'index' in item and 'code' in item and 'desc' in item

    def test_get_unusual_all(self, qc):
        result = qc.get_unusual(MARKET.SZ, count=0)
        assert isinstance(result, list)
        if result:
            assert 'code' in result[0]

    def test_get_index_info(self, qc):
        result = qc.get_index_info(MARKET.SH, '999999')
        assert isinstance(result, list)
        assert len(result) > 0
        idx = result[0]
        assert idx['code'] == '999999'
        assert idx['open'] >= 0 and idx['high'] >= idx['low'] and idx['close'] >= 0

    def test_get_index_info_multi(self, qc):
        result = qc.get_index_info([(MARKET.SH, '999999'), (MARKET.SZ, '399001')])
        assert isinstance(result, list)
        assert len(result) == 2
        for idx in result:
            assert 'code' in idx
            assert idx['open'] >= 0 and idx['high'] >= idx['low']

    def test_get_index_momentum(self, qc):
        result = qc.get_index_momentum(MARKET.SH, '999999')
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], int)

    def test_get_vol_profile(self, qc):
        result = qc.get_vol_profile(MARKET.SZ, '000001')
        assert result is None or isinstance(result, list)

    def test_get_chart_sampling(self, qc):
        result = qc.get_chart_sampling(MARKET.SZ, '000001')
        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], float)

    def test_get_block_file(self, qc):
        result = qc.get_block_file(BLOCK_FILE_TYPE.DEFAULT)
        assert result is not None
        assert isinstance(result, list)
        if result:
            assert 'code' in result[0] and 'blockname' in result[0]

    def test_get_history_orders(self, qc):
        result = qc.get_history_orders(MARKET.SZ, '000001', date(2026, 4, 10))
        assert isinstance(result, list)
        if result:
            o = result[0]
            assert 'price' in o and 'vol' in o
            assert o['price'] > 0 and o['vol'] > 0


class TestQuotationClientQuotesAdjustment:
    """quotes_adjustment 数据处理（内联数据）"""

    def test_quotes_adjustment(self, qc):
        data = [{
            'high': 100000, 'low': 99000, 'open': 99500,
            'close': 100000, 'pre_close': 99500, 'neg_price': -100,
            'open_amount': 100, 'rise_speed': 500,
            'handicap': {'bid': [{'price': 99500, 'vol': 100}], 'ask': [{'price': 100000, 'vol': 100}]},
            'market': None, 'code': None, 'vol': 0,
        }]
        result = qc.quotes_adjustment(data)
        assert len(result) == 1
        assert result[0]['close'] == 1000.0
        assert result[0]['rise_speed'] == '5.00%'
        assert result[0]['handicap']['bid'][0]['price'] == 995.0
        assert 'turnover' not in result[0]
