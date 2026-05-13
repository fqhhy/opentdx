"""抓取各解析器的原始响应 hex，用于分析未知字段含义。"""
import struct
import sys

sys.path.insert(0, '.')

from opentdx.client.standardClient import StandardClient
from opentdx.client.extendedClient import ExtendedClient
from opentdx.client.macStandardClient import MacStandardClient
from opentdx.const import MARKET, EX_MARKET, CATEGORY, BOARD_TYPE


def hexdump(data, label="", offset=0, limit=512):
    data = data[offset:offset + limit]
    lines = [f"\n{'=' * 60}"]
    lines.append(f"  {label} ({len(data)} bytes)")
    lines.append(f"{'=' * 60}")
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"  {i + offset:04x}  {hex_part:<48s}  {ascii_part}")
    return '\n'.join(lines)


def capture_raw(parser_module, class_name, *args, factory=None, **kwargs):
    """调用 parser 并捕获原始 hex response。"""
    import importlib
    mod = importlib.import_module(parser_module)
    cls = getattr(mod, class_name)
    parser = cls(*args, **kwargs)

    if factory is None:
        client = StandardClient()
        client.connect().login()
    else:
        client = factory()

    # Monkey-patch deserialize 来捕获 raw_data
    original_deserialize = parser.deserialize
    raw_data_container = []

    def patched_deserialize(data):
        raw_data_container.append(bytes(data))
        return original_deserialize(data)

    parser.deserialize = patched_deserialize

    try:
        result = client.call(parser)
    except Exception as e:
        print(f"  [WARN] call 异常: {e}")
        result = None

    client.disconnect()

    if raw_data_container:
        return raw_data_container[0], result
    return None, None


def analyze_chart_sampling():
    print("\n" + "=" * 70)
    print("  quotation/ChartSampling — 分析 data[8:34] 26 字节间隙")
    print("=" * 70)

    raw_data, result = capture_raw(
        'opentdx.parser.quotation.chart_sampling', 'ChartSampling',
        MARKET.SZ, '000001'
    )
    if raw_data is None:
        print("  [SKIP] 无响应")
        return

    print(hexdump(raw_data, "完整响应"))
    gap = raw_data[8:34]
    print(f"\n  data[8:34] ({len(gap)} bytes): {gap.hex()}")

    print(f"  <13H> (13 x uint16): {list(struct.unpack('<13H', gap))}")
    print(f"  <H6sHHHHH>           : {list(struct.unpack('<H6sHHHHH', gap))}")
    print(f"  <IIIIIHH>              : {list(struct.unpack('<IIIIIHH', gap))}")
    print(f"  <HHHHHHHHHHHHH>        : {list(struct.unpack('<HHHHHHHHHHHHH', gap))}")

    interval, pre_close, count = struct.unpack('<HfH', raw_data[34:42])
    print(f"\n  data[34:42]: interval={interval}, pre_close={pre_close:.2f}, count={count}")
    print(f"  result ({len(result)} prices): {result[:5] if result else 'None'}...")


def analyze_quotes_list_padding():
    print("\n" + "=" * 70)
    print("  quotation/QuotesList — 分析 10s + 24s 填充")
    print("=" * 70)

    raw_data, result = capture_raw(
        'opentdx.parser.quotation.quotes_list', 'QuotesList',
        CATEGORY.A, 0, 3
    )
    if raw_data is None:
        print("  [SKIP] 无响应")
        return

    _, count = struct.unpack('<HH', raw_data[:4])
    print(f"  count={count}")

    from opentdx.utils.help import get_price

    for rec_idx in range(min(count, 3)):
        pos = 4
        for _ in range(rec_idx):
            pos += 9  # market + code + active1
            for __ in range(9):
                _, pos = get_price(raw_data, pos)
            pos += 4  # amount
            for __ in range(4):
                _, pos = get_price(raw_data, pos)
            for __ in range(4):
                _, pos = get_price(raw_data, pos)
            pos += 56

        offset = pos
        chunk = raw_data[offset:offset + 56]
        print(f"\n  --- 记录 {rec_idx} (offset={offset}) ---")
        print(hexdump(chunk, f"56 字节尾部", offset=0))

        unknown, rise_speed, st, min2, rush, pad1, vol_rs, depth, pad2, active2 = \
            struct.unpack('<Hhhfh10sff24sH', chunk)
        print(f"    unknown={unknown:#06x} rise_speed={rise_speed} short_turnover={st}")
        print(f"    min2_amount={min2} opening_rush={rush} vol_rise_speed={vol_rs}")
        print(f"    depth={depth} active2={active2}")
        print(f"    pad1(10s): {pad1.hex()}")
        print(f"    pad1 as <5H>: {list(struct.unpack('<5H', pad1))}")
        print(f"    pad2(24s): {pad2.hex()}")
        print(f"    pad2 as <12H>: {list(struct.unpack('<12H', pad2))}")
        print(f"    pad2 as <6I>: {list(struct.unpack('<6I', pad2))}")
        print(f"    pad2 as <6f>: {list(struct.unpack('<6f', pad2))}")


def analyze_unusual_byte():
    print("\n" + "=" * 70)
    print("  quotation/Unusual — 分析每记录偏移 +30 的 1 字节")
    print("=" * 70)

    raw_data, result = capture_raw(
        'opentdx.parser.quotation.unusual', 'Unusual',
        MARKET.SH, 0, 20
    )
    if raw_data is None:
        print("  [SKIP] 无响应")
        return

    count = struct.unpack('<H', raw_data[:2])[0]
    print(f"  count={count}")

    byte_stats = {}
    for i in range(min(count, 40)):
        b = raw_data[32 * i + 30]
        byte_stats[b] = byte_stats.get(b, 0) + 1

        market, code, _, utype, _, idx, z = struct.unpack('<H6sBBBHH', raw_data[32 * i + 2:32 * i + 17])
        desc_data = raw_data[32 * i + 17:32 * i + 30]
        hour, ms = struct.unpack('<BH', raw_data[32 * i + 31:32 * i + 34])

        print(f"  [{i:2d}] code={code.decode('gbk').strip():<8s} utype={utype:#04x} "
              f"byte+30={b:#04x} desc_bytes={desc_data.hex()} time={hour:02d}:{ms // 100:02d}:{ms % 100:02d}")

    print(f"\n  字节值分布: {dict(sorted(byte_stats.items()))}")


def analyze_board_list_pad():
    print("\n" + "=" * 70)
    print("  mac_quotation/BoardList — 分析 16x 填充")
    print("=" * 70)

    def factory():
        client = MacStandardClient()
        client.connect()
        return client

    raw_data, result = capture_raw(
        'opentdx.parser.mac_quotation.board_list', 'BoardList',
        0, 0, 3, factory=factory
    )
    if raw_data is None:
        print("  [SKIP] 无响应")
        return

    count_all, total = struct.unpack('<HH', raw_data[:4])
    count = count_all // 2
    print(f"  count_all={count_all} count={count} total={total}")

    for rec_idx in range(min(count, 3)):
        offset = rec_idx * 160 + 4
        fmt = "<H6s16s44sfff H6s16s44sfff"
        fields = struct.unpack(fmt, raw_data[offset:offset + 160])
        (mkt, code, pad1, name, price, rs, pc,
         smkt, scode, pad2, sname, sprice, srs, spc) = fields

        code_str = code.decode('gbk', 'ignore').strip('\x00')
        name_str = name.decode('gbk', 'ignore').strip('\x00')
        scode_str = scode.decode('gbk', 'ignore').strip('\x00')
        sname_str = sname.decode('gbk', 'ignore').strip('\x00')

        print(f"\n  --- 记录 {rec_idx} ---")
        print(f"    board: {mkt}#{code_str} {name_str} price={price:.2f} rs={rs:.2f}% pc={pc:.2f}")
        print(f"    pad1(16s): {pad1.hex()}")
        print(f"    pad1 as <BBHHHHHHI: {list(struct.unpack('<BBHHHHHHI', pad1))}")
        print(f"    symbol: {smkt}#{scode_str} {sname_str} price={sprice:.2f} rs={srs:.2f}% pc={spc:.2f}")
        print(f"    pad2(16s): {pad2.hex()}")
        print(f"    pad2 as <BBHHHHHHI: {list(struct.unpack('<BBHHHHHHI', pad2))}")


def analyze_ex_server_info():
    print("\n" + "=" * 70)
    print("  ex_quotation/ServerInfo — 分析 53 字节间隙")
    print("=" * 70)

    def factory():
        client = ExtendedClient()
        client.connect().login()
        return client

    raw_data, result = capture_raw(
        'opentdx.parser.ex_quotation.server', 'Info',
        factory=factory
    )
    if raw_data is None:
        print("  [SKIP] 无响应")
        return

    print(hexdump(raw_data, "完整响应", limit=400))

    gap1 = raw_data[131:159]
    print(f"\n  gap1 data[131:159] ({len(gap1)} bytes): {gap1.hex()}")
    for fmt_str in ['<7I', '<14H', '<3IQI', '<HHHHHHHHHHHHHH', '<IIIfI', '<IfIfIfI']:
        try:
            vals = struct.unpack(fmt_str, gap1)
            print(f"    {fmt_str}: {list(vals)}")
        except struct.error:
            pass

    gap2 = raw_data[286:311]
    print(f"\n  gap2 data[286:311] ({len(gap2)} bytes): {gap2.hex()}")
    for fmt_str in ['<6IB', '<I5fB', '<3fIfIB', '<IIIIIBB', '<HHHHHHHHHHHHH']:
        try:
            vals = struct.unpack(fmt_str, gap2)
            print(f"    {fmt_str}: {list(vals)}")
        except struct.error:
            pass


def analyze_table():
    print("\n" + "=" * 70)
    print("  ex_quotation/Table — 分析 157 字节间隙")
    print("=" * 70)

    def factory():
        client = ExtendedClient()
        client.connect().login()
        return client

    raw_data, result = capture_raw(
        'opentdx.parser.ex_quotation.table', 'Table',
        0, 1, factory=factory
    )
    if raw_data is None:
        print("  [SKIP] 无响应")
        return

    print(hexdump(raw_data, "完整响应", limit=400))

    gap1 = raw_data[0:35]
    print(f"\n  gap1 data[0:35] ({len(gap1)} bytes): {gap1.hex()}")
    for fmt_str in ['<H33s', '<8I3B', '<17HB', '<II16s13s']:
        try:
            vals = struct.unpack(fmt_str, gap1)
            print(f"    {fmt_str}: {list(vals)}")
        except struct.error:
            pass

    gap2 = raw_data[39:161]
    print(f"\n  gap2 data[39:161] ({len(gap2)} bytes): {gap2.hex()}")
    # Try parsing as 30 uint32s
    print(f"    <30I>: {list(struct.unpack('<30I', gap2[:120]))}")
    # Try as raw string
    try:
        s = gap2.decode('gbk', errors='replace')
        print(f"    gbk string: {repr(s[:80])}")
    except Exception:
        pass

    start = struct.unpack('<I', raw_data[35:39])[0]
    count, ctx_len = struct.unpack('<II', raw_data[161:169])
    ctx = raw_data[169:].decode('gbk', errors='ignore')
    print(f"\n  已知: start={start} count={count} ctx_len={ctx_len}")
    print(f"  ctx preview: {ctx[:200]}...")


if __name__ == '__main__':
    print("=" * 70)
    print("  TDX 解析器 Hex 分析工具")
    print("=" * 70)

    funcs = [
        analyze_chart_sampling,
        analyze_quotes_list_padding,
        analyze_unusual_byte,
        analyze_board_list_pad,
        analyze_ex_server_info,
        analyze_table,
    ]

    for fn in funcs:
        try:
            fn()
        except Exception as e:
            import traceback
            print(f"  [ERROR] {fn.__name__}: {e}")
            traceback.print_exc()
