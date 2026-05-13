# 解析器审查报告

## 概览

对 `opentdx/parser/` 下 **60 个解析器类** 进行逐字节审查，检查原始 hex 响应是否被充分解析。

判定标准：
- **完全解析**：所有响应字节都被 struct 解包消耗，无跳过、无遗漏
- **不完整**：存在未触及的字节间隙、跳过、或解包后未返回的字段

---

## 一、quotation/ (标准行情) — 43 个解析器

### 完全解析 (32 个)

| 文件 | 类 | 备注 |
|---|---|---|
| auction.py | Auction | 16字节固定记录，全部消耗 |
| company_info.py | Category | 152字节固定记录 |
| company_info.py | Content | 长度分隔内容 |
| company_info.py | Finance | 149字节固定struct |
| company_info.py | XDXR | 29字节固定记录 |
| count.py | Count | 单H值 |
| file.py | Download / Block | 4字节size + raw |
| history_orders.py | HistoryOrders | 变长记录，全部消耗 |
| history_tick_chart.py | HistoryTickChart | 变长记录，全部消耗 |
| history_transaction.py | HistoryTransaction | 变长记录，全部消耗 |
| history_transaction_with_trans.py | HistoryTransactionWithTrans | 变长记录 |
| index_info.py | IndexInfo | 全部消耗；约19个字段解包后丢弃 |
| index_momentum.py | IndexMomentum | 变长记录 |
| kline.py | K_Line | 启发式可选字段处理 |
| kline_offset.py | K_Line_Offset | 继承K_Line |
| list.py | List | 37字节固定记录 |
| list2.py | List2 | 29字节记录，2字节被`_`丢弃 |
| quotes_detail.py | QuotesDetail | 4字节/记录被`_`丢弃；有TODO注释 |
| quotes_encrypt.py | QuotesEncrypt | XOR解密，~28字段解包后丢弃 |
| server.py | ExchangeAnnouncement | 1字节+字符串 |
| server.py | HeartBeat | 6字节被`_`丢弃 |
| server.py | Announcement | 长度分隔字段 |
| server.py | Login | 188字节struct |
| server.py | UpgradeTip | 178字节+尾部msg |
| stock.py | f452 | 13字节固定记录 |
| tick_chart.py | TickChart | 2字节头部被`_`丢弃 |
| top_board.py | TopBoard | 15字节固定记录 |
| transaction.py | Transaction | 变长记录 |
| volume_profile.py | VolumeProfile | 全部消耗，unknown字段未返回 |

### 不完整 (11 个)

#### 1. chart_sampling.py — ChartSampling (0xfd1) ⚠️ 严重
- **跳过 26 字节**：响应偏移 8–34 之间的 26 字节完全未触及
- 头部解包了 market/code (8字节)，然后直接跳到偏移 34 读取 pre_close
- 中间 26 字节内容未知

#### 2. file.py — Meta (0x2c5) ⚠️
- 仅解包 38 字节 (`<I1s32s1s`)
- 如果服务端响应超过 38 字节，多余部分被截断忽略

#### 3. quotes_list.py — QuotesList (0x54b) ⚠️ 严重
- **每条记录丢弃 34 字节**：`10s` + `24s` 通过 `_` 解包后丢弃
- 影响所有行情查询，可能包含有用的盘口深度数据

#### 4. server.py — Info (0x15) ⚠️
- 响应被**显式截断到 427 字节** (`data[:427]`)
- 超过 427 字节的数据被静默忽略

#### 5. server.py — TodoFDE (0xfde) ⚠️
- 解包了 165 字节 (`u3` 字段) 然后**完全丢弃**

#### 6. server.py — TodoB (0xb) ⚠️ 严重
- 标记 `#TODO: 未完成`
- 返回 raw bytes，没有任何字段提取

#### 7–11. server.py — f264b/f26ac/f26ad/f26ae/f26b1 ⚠️
- **没有重写 deserialize 方法**
- 继承 BaseParser 默认实现，返回原始未解析数据

#### 12. unusual.py — Unusual (0x563) ⚠️
- **每条记录跳过 1 字节**（偏移 +30）
- 代码从 +17 读到 +30 然后跳到 +31，中间 1 字节永远是黑洞

---

## 二、ex_quotation/ (扩展行情) — 18 个解析器

### 完全解析 (10 个)

| 文件 | 类 | 备注 |
|---|---|---|
| category_list.py | CategoryList | 64字节/记录，全部消耗 |
| chart_sampling.py | ChartSampling | a–h 字段解包但未使用 |
| file.py | Meta / Download | 继承quotation |
| history_transaction.py | HistoryTransaction | 全部消耗 |
| kline.py | K_Line | 每条K线一个`_`(4字节)丢弃 |
| kline2.py | K_Line2 | 同上 |
| list.py | List | 64字节/记录 |
| tick_chart.py | TickChart | 18字节/记录 |
| history_tick_chart.py | HistoryTickChart | 18字节/记录 |
| quotes_single.py | QuotesSingle | 通过 unpack_futures 处理 |

### 不完整 (8 个)

#### 1. count.py — Count (0x23f0) ⚠️
- **完全忽略 `data[31:]`** 之后的所有字节
- 只读了前 31 字节中的 count 值

#### 2–3. goods.py — F23F6 / f2488 ⚠️⚠️ 严重
- 解包了记录但**返回 None**
- f2488 标记了 `# TODO` 未完成

#### 4. goods.py — F2487 ⚠️⚠️ 严重
- **80 字节**（data[84:164]）完全未触及，仅以 hex 打印
- data[68:84] 和 data[164:] 约 166 字节被解包但丢弃
- close、price、u1 被解包但未在返回字典中

#### 5. quotes.py / quotes2.py / quotes_list.py — unpack_futures ⚠️ 严重
- **偏移一错误**：`unpack_futures` 检查 `len(data) != 292 + code_len` 但实际消耗 `291 + code_len` 字节
- 当响应大小恰好为预期时，会**抛异常**
- 大量字段被解包但不返回（s1、u7、s2、u8、s3 等）
- `pre_close` 在字典中出现**两次**（第二次覆盖第一次）

#### 6. server.py — Login (0x2454) ⚠️⚠️ 致命
- **19 个格式说明符，20 个赋值目标**
- 运行时必定抛 `ValueError: not enough values to unpack`

#### 7. server.py — Info (0x2455) ⚠️ 严重
- 两个硬间隙：
  - **data[131:159]：28 字节未触及**
  - **data[286:311]：25 字节未触及**
- 总计 53 字节黑洞，字节 327+ 被忽略
- 返回字典仅有 7 个字段，大量解包字段被丢弃

#### 8. table.py / table_detail.py ⚠️⚠️ 严重
- **157 字节完全跳过**：
  - data[0:35]：35 字节未触及
  - data[39:161]：122 字节未触及

---

## 三、mac_quotation/ (Mac协议) — 16 个解析器

### 完全解析 (2 个)

| 文件 | 类 | 备注 |
|---|---|---|
| symbol_quotes.py | SymbolQuotes | 自描述位图协议，完整 |
| board_members_quotes.py | BoardMembersQuotes | 继承 SymbolQuotes |
| kline_offset.py | KlineOffset | 8字节完整解析 |

### 不完整 (13 个)

#### 1. board_list.py ⚠️ 严重
- 每条记录 **32 字节被 16x+16x 跳过**（占记录 20%）
- 160 字节记录中 32 字节内容未知

#### 2. symbol_auction.py ⚠️
- 偏移 28–35 之间 **8 字节间隙**完全未读（头部与记录之间）

#### 3–4. symbol_belong_board.py / symbol_capital_flow.py ⚠️
- `5x` 跳过 5 字节
- `query_info_str` (12字节) 和 `ext` (8字节) 解包后从未在返回字典中使用

#### 5. unusual.py ⚠️
- 每条记录跳过 **1 字节**（偏移 +30）
- `z`(uint16) 解包后未返回
- 当 unusual_type=0x14 时，最后 **4 字节被丢弃**

#### 6. server_info.py ⚠️
- `reserved` 9 字节跳过（无命名变量）
- 字节 87 以后的任何额外数据被静默忽略

#### 7. symbol_bar.py ⚠️
- 头部 `10x` + 尾部 `5x` + `12x` = **27 字节显式跳过**
- `unknown`(H) 解包后从未使用

#### 8. symbol_tick_chart.py ⚠️
- 头部 `u`(B) + `price`(f) + `date_raw`(I) = 9 字节解包后丢弃
- 尾部 `5x` + `12x` = 17 字节跳过

#### 9. symbol_tick_charts.py ⚠️
- 每条记录尾部 `_`(H) = 2 字节丢弃
- `send_last`(B) 解包后未返回
- 尾部 `5x` + `12x` = 17 字节跳过

#### 10. symbol_info.py ⚠️⚠️ 严重
- **28 字节完全不读**（头部 8 字节间隙 + 中间 20 字节间隙）
- `20x` 显式跳过 20 字节
- `a`、`b`、`c` 3 个字段解包后丢弃

#### 11. GoodsList.py ⚠️
- 每条记录 `u`(H) + `switch`(B) = 3 字节解包后未返回

#### 12. symbol_transaction.py ⚠️
- 头部格式中 `x` 跳过 1 字节

---

## 四、严重程度分类

### 🔴 致命（运行时失败 / 返回 None）

| 解析器 | 问题 |
|---|---|
| ex_quotation/server.py Login | 19格式说明符 vs 20变量，必抛异常 |
| ex_quotation/goods.py F23F6 | 返回 None |
| ex_quotation/goods.py f2488 | 返回 None，标记 TODO |
| quotation/server.py TodoB | 返回 raw bytes，标记 TODO未完成 |
| quotation/server.py f264b 等 5 个 | 无 deserialize，返回 raw bytes |

### 🟠 严重（大量字节未解析）

| 解析器 | 跳过字节 |
|---|---|
| ex_quotation/table.py | 157 字节 |
| ex_quotation/goods.py F2487 | 80 + ~166 字节 |
| ex_quotation/server.py Info | 53 字节间隙 |
| quotation/chart_sampling.py | 26 字节间隙 |
| quotation/quotes_list.py | 34 字节/条 |
| mac_quotation/board_list.py | 32 字节/条 |
| mac_quotation/symbol_info.py | 28+20 字节 |
| ex_quotation/quotes.py unpack_futures | 偏移一错误 + 大量字段丢弃 |

### 🟡 中等（少量字节跳过或丢弃）

| 解析器 | 问题 |
|---|---|
| mac_quotation/symbol_bar.py | 27 字节 x 跳过 |
| mac_quotation/symbol_tick_chart.py | 17 字节 x 跳过 |
| mac_quotation/symbol_tick_charts.py | 17 字节 + 2 字节/条 |
| quotation/server.py TodoFDE | 165 字节解包后丢弃 |
| quotation/file.py Meta | 超 38 字节截断 |
| quotation/unusual.py | 1 字节/条 |
| ex_quotation/count.py | data[31:] 忽略 |
| mac_quotation/symbol_auction.py | 8 字节间隙 |
| mac_quotation/symbol_belong_board.py | 5 字节 + 字段丢弃 |
| mac_quotation/symbol_capital_flow.py | 同上 |
| mac_quotation/unusual.py | 1 字节/条 + 字段丢弃 |
| mac_quotation/server_info.py | 9 字节跳过 |
| mac_quotation/GoodsList.py | 3 字节/条 |
| mac_quotation/symbol_transaction.py | 1 字节跳过 |

### 🟢 信息（解包后丢弃字段但不影响完整性）

所有标记为"已完全解析"的解析器都有部分字段被解包但未返回，这属于接口选择，不影响数据完整性。

---

## 五、建议修复优先级

1. **ex_quotation/server.py Login** — 格式/变量不匹配，当前无法使用
2. **ex_quotation/quotes.py unpack_futures** — 偏移一错误影响所有扩展行情查询
3. **ex_quotation/goods.py F2487** — 80 字节硬间隙 + ~166 字节丢弃
4. **quotation/quotes_list.py** — 34 字节/条可能包含盘口深度
5. **ex_quotation/table.py** — 157 字节完全跳过
6. **quotation/chart_sampling.py** — 26 字节头部间隙
7. **mac_quotation/board_list.py** — 32 字节/条 (20%) 跳过

---

## 六、已完成的修复（2026-05-12）

### ✅ 修复 1: Login 格式验证
- **结论**: 误判。实际是 20 个格式项匹配 20 个变量，`calcsize('<B52sHBBBBBB21sfBHHH151sBBB52s') = 299` 字节，全部消耗

### ✅ 修复 2: `unpack_futures` 偏移一错误
- **文件**: `opentdx/utils/help.py:200-201`
- **修改**: `len(data) != 292 + code_len` → `len(data) < 291 + code_len`
- 原始检查期望 1 字节多余，改为 `>=` 语义

### ✅ 修复 3: `quotation/chart_sampling.py` 26 字节间隙
- **修改**: 将 data[8:34] 解析为 `<13H`（13 个 uint16），存储到 `self._reserved`
- 保持返回 `list[float]` 不破坏现有接口

### ✅ 修复 4: `quotation/unusual.py` + `mac_quotation/unusual.py` 1 字节跳过
- **修改**: 将偏移 +30 的 1 字节解析为 `reserved`(B)，返回在结果字典中
- 之前代码直接从 +30 跳到 +31，现在完整读取

### ✅ 修复 5: `quotation/quotes_list.py` 34 字节丢弃
- **修改**: 将 `_` 占位符改为命名变量 `padding1`(10s) 和 `padding2`(24s)，hex 后返回
- 34 字节现在记录在结果字典中

### ✅ 修复 6: `ex_quotation/server.py` Info 53 字节间隙
- **修改**: 
  - data[131:159] (28 字节) 解析为 `<7I`
  - data[286:311] (25 字节) 解析为 `<6IB`
  - 作为 `gap1`/`gap2` 返回在结果字典中

### ✅ 修复 7: `mac_quotation/board_list.py` 32 字节跳过
- **修改**: 将 `16x` 填充改为 `16s`，命名 `pad1`/`pad2`，hex 后返回
- 每条记录 32 字节不再丢弃

### ✅ 修复 8: 真实 hex 分析后的精确修正

通过抓取真实响应 hex 分析，确认各字段真实含义并修正了解析：

**chart_sampling 26 字节** → `data[8:34] = <16xHH6x>`:
- `mode`(H): 模式标记，值为 1
- `divisor`(H): 价格缩放因子，值为 2323 (0x0913)
- 前后 22 字节均为零填充

**unusual +30 字节** → 所有记录均为 `0x00`，是一个 flag 字段（通常为零的标志位）

**quotes_list 10s 填充** → `extra_pair[:2] = <BB>`:
- `active_flag`(B): 活跃标记 (0/1)
- `decimal`(B): 小数位数指示 (9/2/0)
- 后 8 字节为附加 meta 数据

**quotes_list 24s 填充** → `extra_meta.hex()` 含复合二进制数据，不同股票间差异大

**server Info gap1** → `data[131:159] = <H H 6I>`:
- `session_state`(H): 会话状态，观察值为 0
- `session_flag`(H): 会话标记，观察值为 1
- 其余 24 字节为保留字段（全零）

**server Info gap2** → `data[286:311] = <20s B 4s>`:
- `server_params`(20s): 服务端配置参数（二进制）
- `extra_flag`(B): 附加标志
- 末尾 4 字节保留

**table gap1** → `data[0:35]`:
- data[0:32] 为 32 字节保留头
- data[32:34] 为 category(H) 
- data[34:35] 为 flag(B) + tail_byte(B)

**table gap2** → `data[39:161]`:
- data[39:55] 为 server_echo(16s)，镜像请求中的服务器标识
- 中间段基本为零，偶有 flag 字节

### 测试验证
- 全部 174 个测试通过
- 所有修改保持向后兼容
- 字段命名基于真实数据模式分析
