from datetime import time
import struct
from typing import override

from opentdx.const import MARKET
from opentdx.parser.baseParser import BaseParser, register_parser
from opentdx.utils.help import unpack_by_type


@register_parser(0x563)
class Unusual(BaseParser): # 主力监控
    def __init__(self, market: MARKET, start: int, count: int = 600):
        self.body = struct.pack('<HII', market.value, start, count)

    @override
    def deserialize(self, data):
        count, = struct.unpack('<H', data[:2])
        results = []
        for i in range(count):
            market, code, _, unusual_type, _, index, z = struct.unpack('<H6sBBBHH', data[32 * i + 2: 32 * i + 17])
            desc, value, v1, v2, v3, v4  = unpack_by_type(unusual_type, data[32 * i + 17: 32 * i + 30])
            hour, minute_sec = struct.unpack('<BH', data[32 * i + 31: 32 * i + 34])

            results.append({
                'index': index,
                'market': MARKET(market),
                'code': code.decode('gbk').replace('\x00', ''),
                'time': time(hour, minute_sec // 100, minute_sec % 100),
                'desc': desc,
                'value': value,
                'unusual_type': unusual_type,
                'v1': v1,
                'v2': v2,
                'v3': v3,
                'v4': v4,
            })
        return results
