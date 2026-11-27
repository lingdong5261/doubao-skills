# 表结构（Schema）

本文件是这套经营日报系统的**唯一结构真相**。建表时逐字复制 JSON，不要临时改字段名——日报脚本按字段名取数，改名即断。

## 0. 建库顺序

表之间存在关联，必须按顺序建，否则 `link_table` 找不到目标：

| 顺序 | 表名 | 记录粒度 | 主字段 | 依赖 |
|---|---|---|---|---|
| 1 | 设备台账 | 一台设备一行 | 设备编号 | 无 |
| 2 | 客户与项目 | 一个客户项目一行 | 客户名称 | 无 |
| 3 | 台班记录 | 一台设备 × 一个班次 × 一个客户 | 台班单号 | 设备台账、客户与项目 |
| 4 | 回款记录 | 一笔到账一行 | 回款单号 | 客户与项目 |
| 5 | 成本支出 | 一笔支出(按设备归集)一行 | 支出单号 | 设备台账 |
| 6 | 经营日报留存 | 一天一行（存日报结论） | 日报日期 | 无 |

建议 Base 名：`机械租赁经营日报`。

---

## 1. 设备台账

用途：全公司唯一设备主档。台班、成本只写关联，**不要在每个台班记录里重复手写设备名**，否则统计会散成几十个"25吨吊车"。

| 字段 | 类型 | 说明 |
|---|---|---|
| 设备编号 | text（主字段） | 规则：`QY25-01`（汽车吊25吨1号）、`LD50-01`（履带吊）、`SC12-01`（随车吊）、`PB13-01`（13米平板） |
| 设备名称 | text | 人话名称，如「25吨汽车吊-1号车」 |
| 设备类型 | select | 汽车吊/履带吊/随车吊/平板车/低平板/高栏车 |
| 吨位档 | select | 吊机按额定吨位，平板按载重：8吨/12吨/16吨/25吨/35吨/50吨/80吨/100吨以上 |
| 规格型号 | text | 如 QY25K5、三一 STC250 |
| 车牌号 | text | 无牌设备填「场内」 |
| 台班单价 | number(currency) | 一个标准台班（8小时）报价 |
| 加班小时单价 | number(currency) | 超8小时按小时加收 |
| 月租单价 | number(currency) | 包月报价，用于对照台班口径是否划算 |
| 设备状态 | select | 在租/待租/维修/保养/停用/外协 |
| 归属方式 | select | 自有/外协/挂靠 |
| 机主/车队长 | text | 外协设备填机主姓名 |
| 常驻场地 | text | 便于调度 |
| 进场日期 | datetime | |
| 保险到期日 | datetime | 预警用 |
| 年检到期日 | datetime | 预警用 |

```json
[{"name":"设备编号","type":"text"},
{"name":"设备名称","type":"text"},
{"name":"设备类型","type":"select","options":[{"name":"汽车吊","hue":"Blue"},{"name":"履带吊","hue":"Purple"},{"name":"随车吊","hue":"Turquoise"},{"name":"平板车","hue":"Orange"},{"name":"低平板","hue":"Yellow"},{"name":"高栏车","hue":"Lime"}]},
{"name":"吨位档","type":"select","options":[{"name":"8吨"},{"name":"12吨"},{"name":"16吨"},{"name":"25吨"},{"name":"35吨"},{"name":"50吨"},{"name":"80吨"},{"name":"100吨以上","hue":"Red"}]},
{"name":"规格型号","type":"text"},
{"name":"车牌号","type":"text"},
{"name":"台班单价","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
{"name":"加班小时单价","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
{"name":"月租单价","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
{"name":"设备状态","type":"select","options":[{"name":"在租","hue":"Green"},{"name":"待租","hue":"Blue"},{"name":"维修","hue":"Red"},{"name":"保养","hue":"Orange"},{"name":"停用","hue":"Gray"},{"name":"外协","hue":"Purple"}]},
{"name":"归属方式","type":"select","options":[{"name":"自有","hue":"Green"},{"name":"外协","hue":"Orange"},{"name":"挂靠","hue":"Blue"}]},
{"name":"机主/车队长","type":"text"},
{"name":"常驻场地","type":"text"},
{"name":"进场日期","type":"datetime","style":{"format":"yyyy-MM-dd"}},
{"name":"保险到期日","type":"datetime","style":{"format":"yyyy-MM-dd"}},
{"name":"年检到期日","type":"datetime","style":{"format":"yyyy-MM-dd"}}]
```

---

## 2. 客户与项目

用途：客户 + 在建项目合成一表（小公司一个客户通常对应一个活跃项目，合并可少填一次）。

| 字段 | 类型 | 说明 |
|---|---|---|
| 客户名称 | text（主字段） | 全称，不要简称混用 |
| 客户类型 | select | 总包/分包/甲方直租/中介/同行调车 |
| 项目名称 | text | 如「万科白鹭湾二期」 |
| 项目地址 | text | |
| 联系人 | text | |
| 联系电话 | text(phone) | |
| 业务员 | user(单选) | 业绩归属人 |
| 结算方式 | select | 台班现结/月结/合同节点/预付 |
| 账期天数 | number | 0=现结，30/45/60…；超期预警用 |
| 合同金额 | number(currency) | 可空 |
| 合作状态 | select | 在租/已完工/暂停/已流失 |
| 首次合作日期 | datetime | |

```json
[{"name":"客户名称","type":"text"},
{"name":"客户类型","type":"select","options":[{"name":"总包"},{"name":"分包"},{"name":"甲方直租","hue":"Blue"},{"name":"中介","hue":"Gray"},{"name":"同行调车","hue":"Orange"}]},
{"name":"项目名称","type":"text"},
{"name":"项目地址","type":"text"},
{"name":"联系人","type":"text"},
{"name":"联系电话","type":"text","style":{"type":"phone"}},
{"name":"业务员","type":"user","multiple":false},
{"name":"结算方式","type":"select","options":[{"name":"台班现结"},{"name":"月结","hue":"Blue"},{"name":"合同节点","hue":"Purple"},{"name":"预付","hue":"Green"}]},
{"name":"账期天数","type":"number","style":{"type":"plain","precision":0}},
{"name":"合同金额","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
{"name":"合作状态","type":"select","options":[{"name":"在租","hue":"Green"},{"name":"已完工","hue":"Gray"},{"name":"暂停","hue":"Orange"},{"name":"已流失","hue":"Red"}]},
{"name":"首次合作日期","type":"datetime","style":{"format":"yyyy-MM-dd"}}]
```

---

## 3. 台班记录（核心流水表）

用途：**一次出车/一个工作班次 = 一条记录**。收入、应收、出勤率、设备利用率全部从这张表算出来。日报的口径完全取决于录入是否规范。

| 字段 | 类型 | 说明 |
|---|---|---|
| 台班单号 | auto_number（主字段） | 自动 `TB-yyyyMMdd-001` |
| 日期 | datetime | 作业当天，不要填录入当天 |
| 关联设备 | link→设备台账 | 双向字段名「关联台班记录」 |
| 关联客户 | link→客户与项目 | 双向字段名「关联台班记录」 |
| 项目工地 | text | 与客户表项目名一致，便于工地维度统计 |
| 作业内容 | text | 如「钢梁吊装」「设备转运」 |
| 台班类型 | select | 白班/夜班/包月/临时/半班 |
| 台班数 | number(1位小数) | 标准班=1，半天=0.5，两班=2 |
| 加班小时 | number(1位小数) | 超8小时部分 |
| 台班单价 | number(currency) | 从台账带出，允许现场上浮 |
| 加班单价 | number(currency) | 按小时 |
| 结算状态 | select | 未结算/已结算/部分结算/挂账 |
| 业务员 | user(单选) | 业绩归属，与客户表默认一致 |
| 司机 | text | |
| 备注 | text | |

**派生字段（建表后用 `+field-create` 补）**

| 字段 | 类型 | 表达式 |
|---|---|---|
| 收入金额 | formula | `[台班数]*[台班单价]+[加班小时]*[加班单价]` |
| 待收金额 | formula | `IF([结算状态]="已结算",0,[台班数]*[台班单价]+[加班小时]*[加班单价])` |

```json
[{"name":"台班单号","type":"auto_number","style":{"rules":[{"type":"text","text":"TB-"},{"type":"created_time","date_format":"yyyyMMdd"},{"type":"incremental_number","length":3}]}},
{"name":"日期","type":"datetime","style":{"format":"yyyy-MM-dd"}},
{"name":"关联设备","type":"link","link_table":"设备台账","bidirectional":true,"bidirectional_link_field_name":"关联台班记录"},
{"name":"关联客户","type":"link","link_table":"客户与项目","bidirectional":true,"bidirectional_link_field_name":"关联台班记录"},
{"name":"项目工地","type":"text"},
{"name":"作业内容","type":"text"},
{"name":"台班类型","type":"select","options":[{"name":"白班","hue":"Blue"},{"name":"夜班","hue":"Purple"},{"name":"包月","hue":"Green"},{"name":"临时","hue":"Orange"},{"name":"半班","hue":"Gray"}]},
{"name":"台班数","type":"number","style":{"type":"plain","precision":1}},
{"name":"加班小时","type":"number","style":{"type":"plain","precision":1}},
{"name":"台班单价","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
{"name":"加班单价","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
{"name":"结算状态","type":"select","options":[{"name":"未结算","hue":"Orange"},{"name":"已结算","hue":"Green"},{"name":"部分结算","hue":"Yellow"},{"name":"挂账","hue":"Red"}]},
{"name":"业务员","type":"user","multiple":false},
{"name":"司机","type":"text"},
{"name":"备注","type":"text"}]
```

---

## 4. 回款记录

用途：现金流入流水。日报里的「今日回款」来自这张表；**应收余额不从这里扣减**，应收来自台班记录的「待收金额」（见 metrics 的口径说明）。

| 字段 | 类型 | 说明 |
|---|---|---|
| 回款单号 | auto_number（主字段） | `HK-yyyyMMdd-001` |
| 回款日期 | datetime | 到账日 |
| 关联客户 | link→客户与项目 | 双向字段名「关联回款记录」 |
| 项目名称 | text | |
| 回款金额 | number(currency) | |
| 回款方式 | select | 对公转账/银行承兑/现金/微信支付宝/抵扣 |
| 核销账期 | text | 如「2026年10月」 |
| 登记人 | user(单选) | |
| 备注 | text | |

```json
[{"name":"回款单号","type":"auto_number","style":{"rules":[{"type":"text","text":"HK-"},{"type":"created_time","date_format":"yyyyMMdd"},{"type":"incremental_number","length":3}]}},
{"name":"回款日期","type":"datetime","style":{"format":"yyyy-MM-dd"}},
{"name":"关联客户","type":"link","link_table":"客户与项目","bidirectional":true,"bidirectional_link_field_name":"关联回款记录"},
{"name":"项目名称","type":"text"},
{"name":"回款金额","type":"number","style":{"type":"currency","precision":2,"currency_code":"CNY"}},
{"name":"回款方式","type":"select","options":[{"name":"对公转账","hue":"Green"},{"name":"银行承兑","hue":"Blue"},{"name":"现金","hue":"Gray"},{"name":"微信支付宝","hue":"Turquoise"},{"name":"抵扣","hue":"Orange"}]},
{"name":"核销账期","type":"text"},
{"name":"登记人","type":"user","multiple":false},
{"name":"备注","type":"text"}]
```

---

## 5. 成本支出

用途：把油费、维修、司机工资落到具体设备，才能算单机毛利。**不能归集到某台设备的公共支出**（如场地租金）不录本表，避免污染单机毛利。

| 字段 | 类型 | 说明 |
|---|---|---|
| 支出单号 | auto_number（主字段） | `CB-yyyyMMdd-001` |
| 发生日期 | datetime | |
| 关联设备 | link→设备台账 | 双向字段名「关联成本支出」 |
| 费用类型 | select | 柴油/维修/配件/司机工资/过路费/吊索具/保险/年检/其他 |
| 金额 | number(currency) | |
| 支付对象 | text | |
| 经办人 | user(单选) | |
| 备注 | text | |

```json
[{"name":"支出单号","type":"auto_number","style":{"rules":[{"type":"text","text":"CB-"},{"type":"created_time","date_format":"yyyyMMdd"},{"type":"incremental_number","length":3}]}},
{"name":"发生日期","type":"datetime","style":{"format":"yyyy-MM-dd"}},
{"name":"关联设备","type":"link","link_table":"设备台账","bidirectional":true,"bidirectional_link_field_name":"关联成本支出"},
{"name":"费用类型","type":"select","options":[{"name":"柴油","hue":"Orange"},{"name":"维修","hue":"Red"},{"name":"配件","hue":"Gray"},{"name":"司机工资","hue":"Blue"},{"name":"过路费","hue":"Turquoise"},{"name":"吊索具","hue":"Purple"},{"name":"保险","hue":"Yellow"},{"name":"年检","hue":"Lime"},{"name":"其他","hue":"Gray"}]},
{"name":"金额","type":"number","style":{"type":"currency","precision":2,"currency_code":"CNY"}},
{"name":"支付对象","type":"text"},
{"name":"经办人","type":"user","multiple":false},
{"name":"备注","type":"text"}]
```

---

## 6. 经营日报留存

用途：每天生成日报后回写一行，积累趋势；也方便老板在表里翻历史，不必每天重算。

| 字段 | 类型 | 说明 |
|---|---|---|
| 日报日期 | text（主字段） | `2026-11-22` |
| 台班数 | number(1位) | |
| 收入金额 | number(currency) | |
| 回款金额 | number(currency) | |
| 出勤设备数 | number(0位) | |
| 出勤率 | number(1位,百分比) | 0~100 |
| 成本金额 | number(currency) | 直接成本 |
| 毛利 | number(currency) | |
| 毛利率 | number(1位,百分比) | |
| 生成时间 | created_at | |
| 日报正文 | text | 日报 Markdown 全文 |

```json
[{"name":"日报日期","type":"text"},
{"name":"台班数","type":"number","style":{"type":"plain","precision":1}},
{"name":"收入金额","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
{"name":"回款金额","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
{"name":"出勤设备数","type":"number","style":{"type":"plain","precision":0}},
{"name":"出勤率","type":"number","style":{"type":"plain","precision":1}},
{"name":"成本金额","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
{"name":"毛利","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
{"name":"毛利率","type":"number","style":{"type":"plain","precision":1}},
{"name":"生成时间","type":"created_at","style":{"format":"yyyy-MM-dd HH:mm"}},
{"name":"日报正文","type":"text"}]
```

---

## 7. 录入纪律（日报准不准，全看这几条）

1. **设备必须先上台账**。新设备先进「设备台账」，再录台班；不允许在台班里手打设备名。
2. **一条台班 = 一台设备 × 一个班次 × 一个客户**。同一台设备一天跑两个客户，写两条。
3. **日期填作业当天**。补录昨天就填昨天，不要填今天。
4. **金额不要手填**。收入由公式算；单价从台账带出，现场加价才改。
5. **结算状态默认「未结算」**，收到钱再改；月结客户到期未收改「挂账」。
6. **半天写 0.5 台班**，不要写 1；夜班连白班写 2。
7. 外协设备也要上台账（归属方式=外协），否则出勤率会失真、外协成本无处归集。
