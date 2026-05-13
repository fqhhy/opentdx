"""全面捕获所有解析器的原始 hex，用不同参数类型测试。"""
import sys, struct, traceback
from datetime import date

sys.path.insert(0, '.')
from opentdx.client.standardClient import StandardClient
from opentdx.client.extendedClient import ExtendedClient
from opentdx.client.macStandardClient import MacStandardClient
from opentdx.client.macExtendedClient import MacExtendedClient
from opentdx.const import MARKET, EX_MARKET, PERIOD, CATEGORY, BLOCK_FILE_TYPE, BOARD_TYPE, EX_BOARD_TYPE, SORT_TYPE, ADJUST

def hexdump(data, limit=256):
    lines = []
    for i in range(0, min(len(data), limit), 16):
        chunk = data[i:i+16]
        hx = ' '.join(f'{b:02x}' for b in chunk)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"  {i:04x}  {hx:<48s}  {asc}")
    if len(data) > limit:
        lines.append(f"  ... ({len(data) - limit} more bytes)")
    return '\n'.join(lines)


def capture(parser_cls_path, class_name, factory, *args, **kwargs):
    """调用 parser 并返回原始 hex。"""
    import importlib
    mod = importlib.import_module(parser_cls_path)
    cls = getattr(mod, class_name)
    parser = cls(*args, **kwargs)

    raw_data = []

    original = parser.deserialize
    def patched(data):
        raw_data.append(bytes(data))
        return original(data)
    parser.deserialize = patched

    try:
        client = factory()
        result = client.call(parser)
        client.disconnect()
    except Exception as e:
        return None, str(e)

    return (raw_data[0] if raw_data else None), result


def test_variants(name, parser_path, class_name, factory_fn, variants):
    """对同一个 parser 用不同参数测试。"""
    print(f"\n{'='*70}")
    print(f"  {name}")
    print(f"{'='*70}")
    for label, args, kwargs in variants:
        raw, result = capture(parser_path, class_name, factory_fn, *args, **kwargs)
        if raw is None:
            print(f"  [{label}] [SKIP] error: {result}")
            continue
        print(f"\n  --- {label} ({len(raw)} bytes) ---")
        print(hexdump(raw))
        if result is not None:
            if isinstance(result, list):
                print(f"  result: list[{len(result)}]")
            elif isinstance(result, dict):
                ks = list(result.keys())[:10]
                print(f"  result: dict keys={ks}...")
            else:
                print(f"  result: {type(result).__name__}")


# =============== quotation/ 标准行情 ===============

def test_quotation_remaining():
    """测试 quotation/ 目录剩余未修复的解析器。"""
    def std_factory():
        c = StandardClient()
        c.connect().login()
        return c

    # 1. file.py Meta
    print("\n### quotation/file.py Meta ###")
    raw, _ = capture('opentdx.parser.quotation.file', 'Meta', std_factory, BLOCK_FILE_TYPE.DEFAULT)
    if raw:
        print(hexdump(raw))
        print(f"  parsed: size={struct.unpack('<I', raw[:4])[0]}")
        print(f"  parsed: unknown1={raw[4:5].hex()} hash={raw[5:37].hex()} unknown2={raw[37:38].hex()}")
        if len(raw) > 38:
            print(f"  >>> 超出 38 字节部分: {raw[38:].hex()}")

    # 2. volume_profile - 不同 market/code
    for label, mkt, code in [("000001", MARKET.SZ, '000001'), ("510050(ETF)", MARKET.SH, '510050'),
                               ("159919(ETF)", MARKET.SZ, '159919')]:
        raw, _ = capture('opentdx.parser.quotation.volume_profile', 'VolumeProfile', std_factory, mkt, code)
        if raw:
            print(f"\n  volume_profile {label} ({len(raw)} bytes):")
            print(hexdump(raw, 128))

    # 3. quotes_encrypt - ETF vs stock
    for label, mkt, code in [("000001", MARKET.SZ, '000001'), ("588000(ETF)", MARKET.SH, '588000')]:
        parser_path = 'opentdx.parser.quotation.quotes_encrypt'
        raw, _ = capture(parser_path, 'QuotesEncrypt', std_factory, mkt, code)
        if raw:
            print(f"\n  quotes_encrypt {label} ({len(raw)} bytes):")
            print(hexdump(raw, 128))

    # 4. quotes_detail - stock vs ETF
    for label, mkt, code in [("000001", MARKET.SZ, '000001'), ("510050(ETF)", MARKET.SH, '510050'),
                               ("159915(ETF)", MARKET.SZ, '159915')]:
        raw, _ = capture('opentdx.parser.quotation.quotes_detail', 'QuotesDetail', std_factory, mkt, code)
        if raw:
            print(f"\n  quotes_detail {label} ({len(raw)} bytes):")
            print(hexdump(raw, 200))

    # 5. kline - daily vs minutes, stock vs ETF
    for label, mkt, code, period, cnt in [
        ("000001 daily", MARKET.SZ, '000001', PERIOD.DAILY, 5),
        ("510050 daily", MARKET.SH, '510050', PERIOD.DAILY, 5),
        ("000001 5min", MARKET.SZ, '000001', PERIOD.MINS, 5),
        ("510050 5min", MARKET.SH, '510050', PERIOD.MINS, 5),
    ]:
        raw, _ = capture('opentdx.parser.quotation.kline', 'K_Line', std_factory, mkt, code, period, count=cnt)
        if raw:
            print(f"\n  kline {label} ({len(raw)} bytes):")
            print(hexdump(raw, 200))


# =============== ex_quotation/ 扩展行情 ===============

def test_ex_quotation_remaining():
    """测试 ex_quotation/ 目录剩余未修复的解析器。"""
    def ex_factory():
        c = ExtendedClient()
        c.connect().login()
        return c

    # 1. count.py - 分析 data[31:]
    raw, _ = capture('opentdx.parser.ex_quotation.count', 'Count', ex_factory)
    if raw:
        print("\n### ex_quotation/count.py ###")
        print(hexdump(raw))
        print(f"  data[:31] parsed: {list(struct.unpack('<11s5I', raw[:31]))}")
        if len(raw) > 31:
            print(f"  >>> data[31:] 未解析 ({len(raw)-31} bytes): {raw[31:].hex()}")

    # 2. goods.py F2487 - 不同市场
    for label, mkt, code in [
        ("TSLA", EX_MARKET.US_STOCK, 'TSLA'),
        ("AAPL", EX_MARKET.US_STOCK, 'AAPL'),
        ("00700", EX_MARKET.HK_MAIN_BOARD, '00700'),
    ]:
        raw, _ = capture('opentdx.parser.ex_quotation.goods', 'F2487', ex_factory, mkt, code)
        if raw:
            print(f"\n  goods F2487 {label} ({len(raw)} bytes):")
            print(hexdump(raw, 300))
            # 分析未解析区域
            if len(raw) > 84:
                print(f"  data[84:164] 未解析: {raw[84:164].hex()}")
                try:
                    vals = struct.unpack('<20I', raw[84:164])
                    print(f"    as <20I>: {list(vals)}")
                except: pass
            if len(raw) > 164:
                print(f"  data[164:] 丢弃区 ({len(raw)-164} bytes): {raw[164:].hex()[:100]}...")

    # 3. goods.py F2562 - 不同市场
    for label, mkt_key in [("美股", 30100), ("港股", 20100)]:
        raw, _ = capture('opentdx.parser.ex_quotation.goods', 'F2562', ex_factory, mkt_key, 0, 3)
        if raw:
            print(f"\n  goods F2562 {label} ({len(raw)} bytes):")
            print(hexdump(raw, 200))
            if len(raw) > 2:
                count = struct.unpack('<H', raw[:2])[0]
                print(f"  count={count}")
                if count > 0:
                    record = raw[2:2+48]
                    print(f"  第一条记录: {record.hex()}")
                    vals = struct.unpack('<H23sHIBfffHH', record)
                    print(f"    parsed: {vals}")

    # 4. quotes.py - US vs HK
    for label, mkt, code in [("TSLA", EX_MARKET.US_STOCK, 'TSLA'), ("00700", EX_MARKET.HK_MAIN_BOARD, '00700')]:
        raw, _ = capture('opentdx.parser.ex_quotation.quotes', 'Quotes', ex_factory, mkt, code)
        if raw:
            print(f"\n  ex_quotes {label} ({len(raw)} bytes):")
            print(hexdump(raw, 400))
            # 显示 unpack_futures 未返回的字段
            print(f"  data[:10] header: {list(struct.unpack('<IIH', raw[:10]))}")

    # 5. kline2 - 对比 kline
    for label, mkt, code in [
        ("TSLA kline2", EX_MARKET.US_STOCK, 'TSLA'),
        ("00700 kline2", EX_MARKET.HK_MAIN_BOARD, '00700'),
    ]:
        raw, _ = capture('opentdx.parser.ex_quotation.kline2', 'K_Line2', ex_factory, mkt, code, PERIOD.DAILY, 1, 0, 3)
        if raw:
            print(f"\n  ex_kline2 {label} ({len(raw)} bytes):")
            print(hexdump(raw, 200))

    # 6. table_detail - 对比 table
    raw, _ = capture('opentdx.parser.ex_quotation.table_detail', 'TableDetail', ex_factory, 0)
    if raw:
        print(f"\n  ex_table_detail ({len(raw)} bytes):")
        print(hexdump(raw, 300))


# =============== mac_quotation/ ===============

def test_mac_quotation_remaining():
    """测试 mac_quotation/ 目录剩余未修复的解析器。"""
    def mac_factory():
        c = MacStandardClient()
        c.connect()
        return c

    def me_factory():
        c = MacExtendedClient()
        c.connect()
        return c

    # 1. symbol_auction - 分析 8 字节间隙
    for label, mkt, code in [
        ("000001", MARKET.SZ, '000001'),
        ("510050", MARKET.SH, '510050'),
        ("159919", MARKET.SZ, '159919'),
    ]:
        raw, _ = capture('opentdx.parser.mac_quotation.symbol_auction', 'Auction', mac_factory, mkt, code)
        if raw:
            print(f"\n  symbol_auction {label} ({len(raw)} bytes):")
            print(hexdump(raw, 200))
            # 分析 gap at offset 28-35
            if len(raw) > 36:
                header = raw[:36]
                print(f"  header (0-35): {header.hex()}")
                print(f"  gap (28-35): {header[28:36].hex()}")
                print(f"  gap as HH: {list(struct.unpack('<HH', header[28:32]))}")
                print(f"  gap as II: {list(struct.unpack('<II', header[28:36]))}")

    # 2. symbol_belong_board - ETF
    for label, mkt, code in [("000001", MARKET.SZ, '000001'), ("510050", MARKET.SH, '510050')]:
        raw, _ = capture('opentdx.parser.mac_quotation.symbol_belong_board', 'SymbolBelongBoard', mac_factory, mkt, code)
        if raw:
            print(f"\n  symbol_belong_board {label} ({len(raw)} bytes):")
            print(hexdump(raw, 300))
            hdr = struct.unpack('<H12s5x8s', raw[:27]) if len(raw) >= 27 else None
            print(f"  header fields: market={raw[0] if raw else None} query_info={raw[1:13].hex()} ext={raw[22:27].hex()}")

    # 3. symbol_capital_flow - stock vs ETF
    for label, mkt, code in [("000100", MARKET.SZ, '000100'), ("510050", MARKET.SH, '510050')]:
        raw, _ = capture('opentdx.parser.mac_quotation.symbol_capital_flow', 'SymbolCapitalFlow', mac_factory, mkt, code)
        if raw:
            print(f"\n  symbol_capital_flow {label} ({len(raw)} bytes):")
            print(hexdump(raw, 300))

    # 4. symbol_bar - 不同周期
    for label, mkt, code, period in [
        ("000100 daily", MARKET.SZ, '000100', PERIOD.DAILY),
        ("510050 daily", MARKET.SH, '510050', PERIOD.DAILY),
        ("000100 weekly", MARKET.SZ, '000100', PERIOD.WEEKLY),
    ]:
        raw, _ = capture('opentdx.parser.mac_quotation.symbol_bar', 'SymbolBar', mac_factory, mkt, code, period, count=5)
        if raw:
            print(f"\n  symbol_bar {label} ({len(raw)} bytes):")
            print(hexdump(raw, 256))

    # 5. symbol_info - stock vs ETF
    for label, mkt, code in [
        ("000001", MARKET.SZ, '000001'),
        ("510050", MARKET.SH, '510050'),
        ("159915", MARKET.SZ, '159915'),
    ]:
        raw, _ = capture('opentdx.parser.mac_quotation.symbol_info', 'SymbolInfo', mac_factory, mkt, code)
        if raw:
            print(f"\n  symbol_info {label} ({len(raw)} bytes):")
            print(hexdump(raw, 256))
            if len(raw) > 8:
                print(f"  gap 0-7: {raw[:8].hex()}")
                print(f"  gap 0-7 as HHII: {list(struct.unpack('<HH I', raw[:8]))}")
            if len(raw) > 95:
                print(f"  gap 76-95: {raw[76:96].hex()}")
                print(f"  gap 76-95 as IIIII: {list(struct.unpack('<5I', raw[76:96]))}")

    # 6. symbol_tick_chart - stock vs ETF, with date
    for label, mkt, code, dt in [
        ("000001 today", MARKET.SZ, '000001', None),
        ("510050 today", MARKET.SH, '510050', None),
    ]:
        args = [mkt, code]
        if dt:
            args.append(dt)
        raw, _ = capture('opentdx.parser.mac_quotation.symbol_tick_chart', 'SymbolTickChart', mac_factory, *args)
        if raw:
            print(f"\n  symbol_tick_chart {label} ({len(raw)} bytes):")
            print(hexdump(raw, 300))

    # 7. symbol_tick_charts - 多日
    for label, mkt, code, dt in [
        ("000001 recent", MARKET.SZ, '000001', None),
    ]:
        args = [mkt, code]
        if dt:
            args.append(dt)
        raw, _ = capture('opentdx.parser.mac_quotation.symbol_tick_charts', 'TickCharts', mac_factory, *args)
        if raw:
            print(f"\n  symbol_tick_charts {label} ({len(raw)} bytes):")
            print(hexdump(raw, 400))

    # 8. server_info
    raw, _ = capture('opentdx.parser.mac_quotation.server_info', 'ServerInfo', mac_factory)
    if raw:
        print(f"\n  mac_server_info ({len(raw)} bytes):")
        print(hexdump(raw))
        if len(raw) > 87:
            print(f"  >>> 超出 87 字节部分 ({len(raw)-87} bytes): {raw[87:].hex()}")

    # 9. GoodsList - US vs HK
    for label, mkt_k, start in [("美股", 30100, 0), ("港股", 20100, 0)]:
        raw, _ = capture('opentdx.parser.mac_quotation.goods_list', 'GoodsList', mac_factory, mkt_k, start, 3)
        if raw:
            print(f"\n  GoodsList {label} ({len(raw)} bytes):")
            print(hexdump(raw, 200))
            if len(raw) > 2:
                count = struct.unpack('<H', raw[:2])[0]
                print(f"  count={count}")
                if count > 0:
                    rec = raw[2:2+48]
                    vals = struct.unpack('<H23sHIBfffHH', rec)
                    print(f"  first record: market={vals[0]} code={vals[1].decode('gbk','ignore').strip()}")
                    print(f"    u(H)={vals[2]} switch(B)={vals[3]} u2(I)={vals[4]}")

    # 10. symbol_transaction - stock vs ETF
    for label, mkt, code in [("000001", MARKET.SZ, '000001'), ("510050", MARKET.SH, '510050')]:
        raw, _ = capture('opentdx.parser.mac_quotation.symbol_transaction', 'SymbolTransaction', mac_factory, mkt, code)
        if raw:
            print(f"\n  symbol_transaction {label} ({len(raw)} bytes):")
            print(hexdump(raw, 200))

    # 11. symbol_quotes - quoted vs basic, ETF vs stock
    for label, fields_enum in [("000001 all", None), ("510050 ETF all", None)]:
        raw, _ = capture('opentdx.parser.mac_quotation.symbol_quotes', 'SymbolQuotes', mac_factory,
                         MARKET.SZ if '510050' not in label else MARKET.SH,
                         '000001' if '510050' not in label else '510050')
        if raw:
            cnt = len(raw)
            print(f"\n  symbol_quotes {label} ({cnt} bytes):")
            # 位图前 20 字节
            bitmap = raw[:20]
            print(f"  bitmap (20 bytes): {bitmap.hex()}")
            bits_set = sum(1 for b in bitmap for bit in range(8) if b & (1 << bit))
            print(f"  bits set in bitmap: {bits_set}")
            print(f"  bytes total: {cnt}, header 20+6=26, per-row bits*4={bits_set*4}")
            print(hexdump(raw, min(cnt, 256)))


if __name__ == '__main__':
    tests = [
        ("quotation 剩余", test_quotation_remaining),
        ("ex_quotation 剩余", test_ex_quotation_remaining),
        ("mac_quotation 剩余", test_mac_quotation_remaining),
    ]

    for name, fn in tests:
        print(f"\n{'#'*70}")
        print(f"# {name}")
        print(f"{'#'*70}")
        try:
            fn()
        except Exception as e:
            traceback.print_exc()
