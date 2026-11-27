# doubao-skills

我在豆包（Doubao Work）里自己写的 Agent Skill 合集，按标准 Skill 结构组织：每个目录一个技能，`SKILL.md` 是入口，配套 `references/` 与 `scripts/`。

## 技能列表

| 目录 | 名称 | 用途 |
|---|---|---|
| `equipment-rental-daily-report/` | 机械租赁经营日报 | 机械工程租赁（吊机/汽车吊/履带吊/随车吊、平板车）经营日报系统。在飞书多维表格里建好设备台账、台班记录、客户与项目、回款、成本五张表并录入数据，一键生成按设备类型与吨位、单台设备、客户项目、业务员、结算状态、成本毛利六个维度拆分的日报，并输出超期欠款、证照到期、闲置设备等预警 |
| `goodsSkill/` | 木里家居导购 | 家具小程序里的导购技能：商品搜索、详情、库存、送装报价、下单、订单跟踪、门店信息七个接口的调度与话术约束（价格库存只取接口返回值） |

## 目录结构

```
doubao-skills/
├── equipment-rental-daily-report/
│   ├── SKILL.md                  # 入口：建表流程、日报生成流程、预警规则
│   ├── references/
│   │   ├── schema.md             # 五张表的字段定义（JSON 可逐字复制）
│   │   ├── metrics.md            # 指标口径与预警阈值
│   │   └── report-template.md    # 日报版式、群发文案
│   └── scripts/
│       └── daily_report.py       # 读多维表格记录 → 多维日报 + 预警
└── goodsSkill/
    ├── SKILL.md                  # 入口：导购角色、硬规则、接口调度表
    ├── mcp.json                  # 七个接口的 schema 与 UI 元信息
    ├── index.js                  # 技能入口
    ├── apis/                     # 各接口实现（goodsSearch / orderCreate / ...）
    └── lib/                      # 请求与格式化工具
```

## 怎么用

**equipment-rental-daily-report**：依赖 `lark-cli`（飞书 CLI，身份 `--as user`）。按 `SKILL.md` 的「首次接入」在飞书建 Base 并建六张表，录数据后运行 `scripts/daily_report.py` 出日报。

```bash
python scripts/daily_report.py --base-token <base_token> --date 2026-11-27
```

**goodsSkill**：是嵌在小程序项目里的技能模块，依赖项目自身的 `pages/` 页面路径与后端接口，单独拷贝出来不能直接跑，需要放回 `miniprogram/skills/` 下使用。

## Notes

- 两个技能都只含指令与代码，不含任何密钥；接口地址与 token 由运行环境注入。
- `goodsSkill` 里的商品价格、库存、门店信息均为示例数据，实际以接口返回为准。
