---
name: equipment-rental-daily-report
description: 机械工程租赁（吊机/汽车吊/履带吊/随车吊、平板车/低平板）的经营日报系统：在飞书多维表格里建好设备台账、台班记录、客户与项目、回款、成本五张表并录入数据，就能一键生成按设备类型与吨位、单台设备、客户项目、业务员、结算状态、成本毛利六个维度拆分的经营日报，并输出超期欠款、证照到期、闲置设备等预警。当用户提到机械租赁、吊车/吊机/吊车出租、平板车、台班、包月、出勤率、出租率、经营日报/生产日报/车队日报，或要求把租赁业务录进飞书多维表格再出日报时使用。
---

# 机械租赁经营日报

## 这套系统在干什么

```
设备台账 ─┐
客户与项目 ┼→ 台班记录（一天一条流水）─┐
           │                          ├→ daily_report.py → 多维日报 + 预警
成本支出 ──┴→ 回款记录（现金流）───────┘
                          └→ 经营日报留存（每天一行趋势）
```

一条台班 = 一台设备 × 一个工作班次 × 一个客户。收入、出勤率、应收、单机毛利全部从台班记录长出来，**录入不规范，日报就是错的**。

三份参考文件，按需读：

| 文件 | 何时读 |
|---|---|
| [references/schema.md](references/schema.md) | 建表、改结构、加字段时；JSON 逐字复制 |
| [references/metrics.md](references/metrics.md) | 解释指标、改口径、调预警阈值时 |
| [references/report-template.md](references/report-template.md) | 改写日报版式、发群、口头汇报时 |

---

## 一、首次接入：把系统建到飞书

用 `lark-cli base`，身份一律 `--as user`。写操作前先 `+table-list` 确认现状，**不重复建**。

1. 读 `references/schema.md`，按「建库顺序」取六段 `--fields` JSON，落到临时文件（见下方「JSON 传参」）。
2. 建 Base + 第一张表：

```bash
lark-cli base +base-create --name "机械租赁经营日报" --table-name "设备台账" \
  --fields "$(cat t1.json)" --time-zone "Asia/Shanghai" --as user \
  --jq '{token:.data.base.base_token,url:.data.base.url,table:.data.table.id}'
```

3. 依次建 客户与项目 → 台班记录 → 回款记录 → 成本支出 → 经营日报留存（顺序不能乱，`link_table` 必须能找到目标表）。每张表 `--jq '.data.table.id'` 存下 table_id。
4. 给台班记录补两个公式字段（必带 `--i-have-read-guide`）：

```
收入金额 = [台班数]*[台班单价]+[加班小时]*[加班单价]
待收金额 = IF([结算状态]="已结算",0,[台班数]*[台班单价]+[加班小时]*[加班单价])
```

5. 建视图（四张，缺一不可，否则老板只能看原始流水）：
   - 台班记录 · `kanban`「回款跟进看板」→ `+view-set-group` 按 `结算状态`
   - 台班记录 · `grid`「未结算台班」→ `+view-set-filter` 结算状态 ∈ {未结算,部分结算,挂账}
   - 设备台账 · `grid`「待租可派车」→ 筛选 `设备状态=待租`，按台班单价降序
   - 设备台账 · `gallery`「设备档案卡」
6. 建仪表盘「经营总览看板」，七个组件按 48 列布局（可直接复用）：

| 组件 | type | 位置 x,y,w,h | 数据 |
|---|---|---|---|
| 本月产值 | statistics | 0,0,12,8 | 台班记录 SUM 收入金额，日期=CurrentMonth |
| 本月台班数 | statistics | 12,0,12,8 | 台班记录 SUM 台班数，同上 |
| 本月回款 | statistics | 24,0,12,8 | 回款记录 SUM 回款金额，回款日期=CurrentMonth |
| 应收余额 | statistics | 36,0,12,8 | 台班记录 SUM 待收金额，不筛选 |
| 每日产值趋势 | line | 0,8,32,24 | 经营日报留存 SUM 收入金额，按日报日期分组 |
| 产值按结算状态 | pie | 32,8,16,12 | 台班记录 SUM 收入金额，按结算状态，本月 |
| 产值按工地 | column | 32,20,16,12 | 台班记录 SUM 收入金额，按项目工地，本月 |

全部建完必须调 `+dashboard-layout` 提交全部坐标收尾。

7. 每张表写 5~10 条样例（新表不得留空），再交付 `base.url`。

**JSON 传参（Windows/PowerShell 易踩坑）**
- 长 JSON 用文件传：`--json "@C:\Users\<你>\AppData\Local\Temp\x.json"`，不要用字符串在 shell 里拼引号（`""` 会原样落进 JSON 导致 `invalid JSON`）。
- `--json @file` 的文件必须落在 `cwd`、`~/AppData/Local/Temp`、`~/.doubao` 之一，否则报 `outside the built-in allowlist`。先 `Copy-Item` 到 `$env:TEMP` 再传。
- `--fields` 支持变量：`$f = Get-Content -Raw -Encoding utf8 t1.json`，再 `--fields $f`。

---

## 二、日常录入

### 1) 对话直录（最常用）

用户说人话，你翻译成记录。例：「今天25吨吊车给万科干了1个台班，加班2小时」→ 建一条台班记录。

解析规则：
- 设备 → 先在设备台账按「吨位档 + 设备类型 + 状态≠停用」定位 `record_id`，**多条命中就问是哪台车，不要自己挑**；台账里没有的新车，先建台账再建台班。
- 客户 → 按客户名称定位；新客户先建「客户与项目」。
- 没说日期 → 用今天；说「昨天/前天」→ 先用计算工具换算成具体日期。
- 没说台班数 → 默认 1；说「半天」→ 0.5；说「连班/两班」→ 2。
- 没说台班单价 → 从设备台账的「台班单价」带出，并同步写入记录（便于对账）。
- 金额字段不填，公式自动算；结算状态默认 `未结算`（说「现结/已收」才改 `已结算`）。
- 业务员：用户没指定就填当前用户；填不了留空会在日报里报"业务员缺失"。

### 2) 表格手工填 / 3) 现场表单 / 4) Excel 导入

手工填和 Excel 导入都要守住「一条台班一行、设备用关联不用手打」；导入走 Drive `+import`，不要把 Excel 拆成逐条 `record-batch-create`。需要司机扫码报班时再建表单（`+form-create`），题目只要：日期、设备、客户、台班数、加班小时、司机、备注。

---

## 三、生成日报（核心流程）

### 第 1 步：定日期

用户说「今天」→ 系统当天；「昨天/前天/上周某天」→ 先用日期计算工具拿到 `YYYY-MM-DD`，**不要自己推**。

### 第 2 步：导出五张表

```bash
BT=<base_token>
lark-cli base +table-list --base-token $BT --as user --jq '.data.tables[] | {id,name}'

lark-cli base +record-list --base-token $BT --table-id <台班记录> --as user \
  --format json --limit 200 | Out-File -Encoding utf8 "$env:TEMP\shifts.json"
```

其余四张同理（equipment / customers / payments / costs）。记录超过 200 条要翻页：加 `--offset 200` 再导一次，把两个文件都传给脚本（`--shifts a.json b.json`）。

### 第 3 步：跑脚本

```bash
python scripts/daily_report.py --date 2026-11-22 \
  --shifts "$env:TEMP\shifts.json" --equipment "$env:TEMP\equipment.json" \
  --customers "$env:TEMP\customers.json" --payments "$env:TEMP\payments.json" \
  --costs "$env:TEMP\costs.json" --out report.md --json-out metrics.json
```

脚本只算不猜：某表当天没记录就按 0，绝不估数。字段名被改过会直接少算——发现某维度为空，先 `+field-list` 核对字段名是不是被改了。

### 第 4 步：核对三个数

- 产值：今日台班收入合计 ≈ 各维度产值之和
- 出勤：出勤台数 ≤ 在册台数
- 应收：应收余额 = 各客户应收之和

对不上就是录入或关联有问题，**先查数据再发日报**，不要改脚本迁就数据。

### 第 5 步：回写「经营日报留存」

用 `metrics.json` 里的数字建一行（日报日期、台班数、收入、回款、出勤数、出勤率、成本、毛利、毛利率、日报正文）。历史趋势和仪表盘折线都靠这张表。

### 第 6 步：送达

| 方式 | 做法 |
|---|---|
| 对话 | 直接贴完整版 Markdown（模板见 report-template.md） |
| 飞书群 | 用 lark-im 发短版文案，末尾带多维表格链接 |
| 飞书文档 | 存一篇文档，一天一节，便于回溯 |
| 定时 | 用多维表格自动化（Workflow）每天固定时间汇总推送，不要用外部定时任务 |

---

## 四、口径与维度

完整定义在 `references/metrics.md`，日报必须按它出。三条最容易错的：

1. **出勤率** = 当日有台班的设备数 ÷ 在册设备数（不含停用），不是台班数 ÷ 设备数。
2. **直接成本** 只含柴油、维修、配件、司机工资、过路费、吊索具、其他；保险和年检不进单日成本。
3. **应收** 取台班记录的「待收金额」，不是回款表的余额差。部分结算按未收全额计（保守口径）。

---

## 五、预警

红：超期应收（账龄 > 客户账期且 ≥5000）、证照 15 天内到期、单机当日毛利倒挂。
黄：待租连续 3 天零台班、未结算超 30 天、业务员缺失、单客户占比 >50%、外协占比 >40%、出勤率 <60%。

没有命中就写「今日无预警」。**不要为了显得有用硬凑预警**。

---

## 六、排错

| 现象 | 处理 |
|---|---|
| `field not found` / 某维度全空 | 字段名被改；`+field-list` 核对，改回或同步改脚本常量 |
| 台班记录了但日报没算进去 | 检查「日期」是否为作业当天（不是录入当天） |
| 设备维度出现「未关联设备的台班」 | 台班记录的「关联设备」为空，补关联 |
| `invalid JSON` | 改用 `--json @file`，文件放 `$env:TEMP` |
| 创建报 API error [1] | 先 `+table-list` / `+dashboard-block-list` 查是否已建，不重复创建 |
| 记录写入超时 | 先 `+record-list` 查是否已写入，确认失败再重试 |

---

## 七、交付验收清单

- [ ] 六张表齐全，字段名与 schema.md 一致
- [ ] 台班记录的「收入金额」「待收金额」是公式，不是手填
- [ ] 每条台班都能追到一台台账设备和一个客户
- [ ] 四张视图存在，看板能开
- [ ] 仪表盘七个组件齐全、无重叠、每行拼满 48
- [ ] 日报十个章节齐全，十、口径章节保留
- [ ] 所有数字与 `metrics.json` 一致
