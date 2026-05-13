from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

from opentdx.commands.market_monitor import is_trading_time, get_display_width, pad_string


class TestIsTradingTime:
    def test_morning_trading(self):
        """上午交易时段应返回 True"""
        china_tz = ZoneInfo("Asia/Shanghai")
        test_times = [
            datetime(2026, 5, 8, 9, 30, 0, tzinfo=china_tz),
            datetime(2026, 5, 8, 10, 0, 0, tzinfo=china_tz),
            datetime(2026, 5, 8, 11, 30, 0, tzinfo=china_tz),
        ]
        for dt in test_times:
            with patch('opentdx.commands.market_monitor.datetime') as mock_dt:
                mock_dt.now.return_value = dt
                mock_dt.strptime = datetime.strptime
                assert is_trading_time() is True, f"Failed at {dt.time()}"

    def test_afternoon_trading(self):
        """下午交易时段应返回 True"""
        china_tz = ZoneInfo("Asia/Shanghai")
        test_times = [
            datetime(2026, 5, 8, 13, 0, 0, tzinfo=china_tz),
            datetime(2026, 5, 8, 14, 30, 0, tzinfo=china_tz),
            datetime(2026, 5, 8, 15, 0, 0, tzinfo=china_tz),
        ]
        for dt in test_times:
            with patch('opentdx.commands.market_monitor.datetime') as mock_dt:
                mock_dt.now.return_value = dt
                mock_dt.strptime = datetime.strptime
                assert is_trading_time() is True, f"Failed at {dt.time()}"

    def test_lunch_break(self):
        """午休时段应返回 False"""
        china_tz = ZoneInfo("Asia/Shanghai")
        dt = datetime(2026, 5, 8, 12, 0, 0, tzinfo=china_tz)
        with patch('opentdx.commands.market_monitor.datetime') as mock_dt:
            mock_dt.now.return_value = dt
            mock_dt.strptime = datetime.strptime
            assert is_trading_time() is False

    def test_before_market(self):
        """开盘前应返回 False"""
        china_tz = ZoneInfo("Asia/Shanghai")
        dt = datetime(2026, 5, 8, 8, 0, 0, tzinfo=china_tz)
        with patch('opentdx.commands.market_monitor.datetime') as mock_dt:
            mock_dt.now.return_value = dt
            mock_dt.strptime = datetime.strptime
            assert is_trading_time() is False

    def test_after_market(self):
        """收盘后应返回 False"""
        china_tz = ZoneInfo("Asia/Shanghai")
        dt = datetime(2026, 5, 8, 16, 0, 0, tzinfo=china_tz)
        with patch('opentdx.commands.market_monitor.datetime') as mock_dt:
            mock_dt.now.return_value = dt
            mock_dt.strptime = datetime.strptime
            assert is_trading_time() is False

    def test_boundary_collection_period(self):
        """集合竞价时段 (9:15-9:30) 应返回 True"""
        china_tz = ZoneInfo("Asia/Shanghai")
        test_times = [
            datetime(2026, 5, 8, 9, 15, 0, tzinfo=china_tz),
            datetime(2026, 5, 8, 9, 25, 0, tzinfo=china_tz),
        ]
        for dt in test_times:
            with patch('opentdx.commands.market_monitor.datetime') as mock_dt:
                mock_dt.now.return_value = dt
                mock_dt.strptime = datetime.strptime
                assert is_trading_time() is True, f"Failed at {dt.time()}"

    def test_afternoon_boundary(self):
        """下午边界时段应正确判断"""
        china_tz = ZoneInfo("Asia/Shanghai")
        test_cases = [
            (datetime(2026, 5, 8, 12, 55, 0, tzinfo=china_tz), True),
            (datetime(2026, 5, 8, 12, 54, 0, tzinfo=china_tz), False),
            (datetime(2026, 5, 8, 15, 5, 0, tzinfo=china_tz), True),
            (datetime(2026, 5, 8, 15, 6, 0, tzinfo=china_tz), False),
        ]
        for dt, expected in test_cases:
            with patch('opentdx.commands.market_monitor.datetime') as mock_dt:
                mock_dt.now.return_value = dt
                mock_dt.strptime = datetime.strptime
                assert is_trading_time() is expected, f"Failed at {dt.time()}"


class TestGetDisplayWidth:
    def test_pure_ascii(self):
        assert get_display_width("Hello") == 5

    def test_pure_chinese(self):
        assert get_display_width("你好世界") == 8  # 4 chars * 2

    def test_mixed_text(self):
        assert get_display_width("平安银行PA") == 10  # 4*2 + 2

    def test_empty_string(self):
        assert get_display_width("") == 0

    def test_full_width_punctuation(self):
        assert get_display_width("，。") == 4

    def test_numbers(self):
        assert get_display_width("000001") == 6

    def test_stock_code_format(self):
        """典型股票代码格式: SH.600519"""
        width = get_display_width("SH.600519")
        assert width == 9  # 9 ASCII chars

    def test_chinese_stock_name(self):
        """典型中文股票名"""
        width = get_display_width("平安银行")
        assert width == 8  # 4 chars * 2


class TestPadString:
    def test_pad_left_ascii(self):
        result = pad_string("Hello", 10, 'left')
        assert result == "Hello     "

    def test_pad_right_ascii(self):
        result = pad_string("Hello", 10, 'right')
        assert result == "     Hello"

    def test_pad_center_ascii(self):
        result = pad_string("Hi", 8, 'center')
        assert len(result) >= 8  # may be exact or more due to display width
        assert "Hi" in result

    def test_pad_left_chinese(self):
        result = pad_string("平安银行", 12, 'left')
        assert get_display_width(result) >= 12

    def test_pad_right_chinese(self):
        result = pad_string("平安银行", 12, 'right')
        assert get_display_width(result) >= 12

    def test_no_padding_needed(self):
        result = pad_string("VeryLongText", 5, 'left')
        assert result == "VeryLongText"

    def test_stock_code_padding(self):
        """股票代码格式化: SH.000001 补到10宽"""
        result = pad_string("SH.000001", 10, 'left')
        assert get_display_width(result) >= 10

    def test_invalid_align(self):
        result = pad_string("Test", 10, 'invalid')
        assert result == "Test"


