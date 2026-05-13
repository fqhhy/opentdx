"""
非阻塞 socket + customize 防串台 针对性测试
"""
import threading
import time
import pytest
from concurrent.futures import Future

from opentdx.client.transport import ResponseDispatcher, Transport
from opentdx.parser.baseParser import BaseParser
from opentdx.client.standardClient import StandardClient
from opentdx.const import MARKET, PERIOD


# ========================
# Unit Tests — 不需要服务器
# ========================

class TestResponseDispatcher:
    """ResponseDispatcher 单元测试"""

    def test_register_returns_future(self):
        rd = ResponseDispatcher()
        f = rd.register(1)
        assert isinstance(f, Future)
        assert not f.done()

    def test_resolve_sets_result(self):
        rd = ResponseDispatcher()
        f = rd.register(42)
        rd.resolve(42, b'hello world')
        assert f.done()
        assert f.result() == b'hello world'

    def test_resolve_unknown_customize_noop(self):
        rd = ResponseDispatcher()
        rd.resolve(999, b'ghost')

    def test_reject_sets_exception(self):
        rd = ResponseDispatcher()
        f = rd.register(7)
        rd.reject(7, RuntimeError("test"))
        with pytest.raises(RuntimeError, match="test"):
            f.result()

    def test_reject_unknown_customize_noop(self):
        rd = ResponseDispatcher()
        rd.reject(888, RuntimeError("ghost"))

    def test_reject_all_rejects_all_pending(self):
        rd = ResponseDispatcher()
        f1 = rd.register(1)
        f2 = rd.register(2)
        f3 = rd.register(3)

        rd.resolve(2, b'done')  # f2 已完成

        rd.reject_all(ConnectionError("disconnected"))

        # f2 已完成，不受影响
        assert f2.result() == b'done'

        # f1, f3 被拒绝
        with pytest.raises(ConnectionError, match="disconnected"):
            f1.result()
        with pytest.raises(ConnectionError, match="disconnected"):
            f3.result()

    def test_multiple_threads_register(self):
        rd = ResponseDispatcher()
        results = []

        def worker(cid):
            f = rd.register(cid)
            time.sleep(0.05)
            rd.resolve(cid, f'data-{cid}'.encode())
            results.append(f.result())

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sorted(results) == [f'data-{i}'.encode() for i in range(10)]

    def test_same_customize_replaced(self):
        """重复 register 同一 customize 应覆盖旧 Future"""
        rd = ResponseDispatcher()
        f1 = rd.register(5)
        f2 = rd.register(5)
        rd.resolve(5, b'new data')
        assert not f1.done()
        assert f2.done()
        assert f2.result() == b'new data'


class TestBaseParserCustomize:
    """Parser customize 实例属性"""

    def test_default_customize_zero(self):
        p = BaseParser()
        assert p.customize == 0

    def test_set_customize_on_instance(self):
        p = BaseParser()
        p.customize = 12345
        data = p.serialize()
        import struct
        head, cid, control, zipsize, unzip_size = struct.unpack('<BIBHH', data[:10])
        assert cid == 12345

    def test_class_customize_unchanged(self):
        """实例属性不影响类属性"""
        p = BaseParser()
        assert p.customize == 0
        p.customize = 999
        p2 = BaseParser()
        assert p2.customize == 0


class TestTransportInit:
    """Transport 初始化测试"""

    def test_default_sync(self):
        t = Transport()
        assert t.nonblocking is False
        assert t._dispatcher is None
        assert t._reader_thread is None

    def test_nonblocking_mode(self):
        t = Transport(nonblocking=True)
        assert t.nonblocking is True

    def test_customize_counter_uniqueness(self):
        t = Transport()
        ids = [t._next_customize() for _ in range(100)]
        assert len(set(ids)) == 100
        assert min(ids) >= 1


# ========================
# Integration Tests — 需要真实服务器
# ========================

@pytest.fixture(scope="module")
def sync_client():
    """默认同步模式客户端"""
    client = StandardClient(multithread=True, heartbeat=False, nonblocking=False)
    client.connect().login()
    yield client
    client.disconnect()


@pytest.fixture(scope="module")
def async_client():
    """非阻塞模式客户端"""
    client = StandardClient(multithread=True, heartbeat=False, nonblocking=True)
    client.connect().login()
    assert client._t._reader_thread is not None
    assert client._t._reader_thread.is_alive()
    yield client
    client.disconnect()


class TestSyncBackwardCompat:
    """同步模式向后兼容测试"""

    def test_get_count(self, sync_client):
        result = sync_client.get_count(MARKET.SZ)
        assert isinstance(result, int)
        assert result > 1000

    def test_get_kline(self, sync_client):
        result = sync_client.get_kline(MARKET.SZ, '000001', PERIOD.DAILY, count=10)
        assert isinstance(result, list)
        assert len(result) == 10
        for k in result:
            assert 'datetime' in k and 'open' in k
            assert k['high'] >= k['low']

    def test_get_quotes(self, sync_client):
        result = sync_client.get_quotes(MARKET.SZ, '000001')
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['code'] == '000001'
        assert result[0]['pre_close'] > 0


class TestAsyncBasic:
    """非阻塞模式基础功能测试"""

    def test_reader_thread_running(self, async_client):
        t = async_client._t
        assert t._reader_thread is not None
        assert t._reader_thread.is_alive()

    def test_get_count(self, async_client):
        result = async_client.get_count(MARKET.SZ)
        assert isinstance(result, int)
        assert result > 1000

    def test_get_kline(self, async_client):
        result = async_client.get_kline(MARKET.SZ, '000001', PERIOD.DAILY, count=10)
        assert isinstance(result, list)
        assert len(result) == 10
        for k in result:
            assert 'datetime' in k and 'open' in k
            assert k['high'] >= k['low']

    def test_get_quotes(self, async_client):
        result = async_client.get_quotes(MARKET.SZ, '000001')
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['code'] == '000001'
        assert result[0]['pre_close'] > 0

    def test_multiple_requests_sequential(self, async_client):
        for i in range(5):
            result = async_client.get_count(MARKET.SZ)
            assert isinstance(result, int)
            assert result > 1000


class TestAsyncConcurrency:
    """并发测试 — 防串台"""

    def test_concurrent_no_crosstalk(self, async_client):
        """5 个线程同时发不同请求，验证返回数据不串台"""
        errors = []
        results = {}

        def worker(thread_id):
            try:
                market = MARKET.SZ if thread_id % 2 == 0 else MARKET.SH
                count = async_client.get_count(market)
                results[thread_id] = count
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"errors: {errors}"
        assert len(results) == 5
        for val in results.values():
            assert isinstance(val, int)
            assert val > 1000

    def test_concurrent_mixed_requests(self, async_client):
        """多线程混合不同类型的请求，验证返回类型正确"""
        errors = []
        results = {}

        def worker(thread_id):
            try:
                if thread_id % 3 == 0:
                    r = async_client.get_count(MARKET.SZ)
                    results[thread_id] = ('count', r)
                elif thread_id % 3 == 1:
                    r = async_client.get_kline(MARKET.SZ, '000001', PERIOD.DAILY, count=5)
                    results[thread_id] = ('kline', r)
                else:
                    r = async_client.get_quotes(MARKET.SZ, '000001')
                    results[thread_id] = ('quotes', r)
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"errors: {errors}"
        assert len(results) == 6

        for tid, (rtype, data) in results.items():
            if rtype == 'count':
                assert isinstance(data, int) and data > 1000
            elif rtype == 'kline':
                assert isinstance(data, list) and len(data) == 5
                assert data[0]['high'] >= data[0]['low']
            elif rtype == 'quotes':
                assert isinstance(data, list) and len(data) == 1
                assert data[0]['pre_close'] > 0

    def test_high_concurrency(self, async_client):
        errors = []

        def worker(_idx):
            try:
                count = async_client.get_count(MARKET.SZ)
                assert count > 0
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"{len(errors)} errors: {errors[:3]}"


class TestAsyncDisconnect:
    """断连处理测试"""

    def test_disconnect_cleans_up(self):
        """disconnect 后 reader 线程应退出"""
        client = StandardClient(nonblocking=True)
        client.connect().login()
        t = client._t
        assert t._reader_thread.is_alive()

        client.disconnect()

        assert t._reader_thread is None
        assert t._dispatcher is None
        assert t._stop_event is None

    def test_call_after_disconnect_returns_none(self):
        """断连后调用应返回 None"""
        client = StandardClient(nonblocking=True)
        client.connect().login()
        client.disconnect()

        result = client.get_count(MARKET.SZ)
        assert result is None
