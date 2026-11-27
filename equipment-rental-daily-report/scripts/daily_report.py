#!/usr/bin/env python3
"""机械工程租赁 · 经营日报计算引擎

输入：lark-cli base +record-list --format json 导出的表记录（或同结构的 dict 列表）
输出：多维经营日报 Markdown + 指标 JSON

用法：
  python daily_report.py --date 2026-11-22 \
      --shifts shifts.json --equipment equipment.json --customers customers.json \
      --payments payments.json --costs costs.json \
      --out report.md --json-out metrics.json

只依赖标准库。所有数字来自传入的记录，不估算、不补造。
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------- 读数据


def _extract(obj):
    """把各种可能的 JSON 形状归一成 [{字段名: 值}]"""
    out = []
    if isinstance(obj, list):
        for x in obj:
            if isinstance(x, dict):
                out.append(x)
        return out
    if not isinstance(obj, dict):
        return out

    d = obj.get("data", obj)
    if isinstance(d, dict) and "fields" in d and "data" in d:
        fields = d["fields"]
        rows = d["data"] or []
        ids = d.get("record_id_list") or []
        for i, r in enumerate(rows):
            if not isinstance(r, list):
                continue
            row = {}
            for j, name in enumerate(fields):
                row[name] = r[j] if j < len(r) else None
            row["_id"] = ids[i] if i < len(ids) else None
            out.append(row)
        return out
    if isinstance(d, dict) and "records" in d and isinstance(d["records"], list):
        return [x for x in d["records"] if isinstance(x, dict)]
    if isinstance(d, list):
        return [x for x in d if isinstance(x, dict)]
    if "fields" in obj and "data" in obj:
        return _extract({"data": {"fields": obj["fields"], "data": obj["data"]}})
    return out


def load_table(paths):
    rows = []
    for p in paths or []:
        try:
            with open(p, encoding="utf-8-sig") as f:
                obj = json.load(f)
        except UnicodeDecodeError:
            with open(p, encoding="gb18030") as f:
                obj = json.load(f)
        got = _extract(obj)
        if not got:
            print(f"[warn] 未从 {p} 解析到记录，确认导出用的是 --format json", file=sys.stderr)
        rows.extend(got)
    return rows


# ---------------------------------------------------------------- 值归一


def txt(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, dict):
        for k in ("text", "name", "value", "full_address"):
            if k in v:
                return txt(v[k])
        return ""
    if isinstance(v, list):
        return "".join(txt(x) for x in v)
    return str(v)


def num(v):
    if v is None or isinstance(v, bool):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.replace(",", "").replace("¥", "").replace("%", "").strip()
        if not s:
            return 0.0
        try:
            return float(s)
        except ValueError:
            return 0.0
    if isinstance(v, list):
        return sum(num(x) for x in v)
    if isinstance(v, dict):
        for k in ("value", "number", "text"):
            if k in v:
                return num(v[k])
    return 0.0


def ids_of(v):
    """link / user 单元格 -> id 列表"""
    res = []
    if isinstance(v, dict):
        if isinstance(v.get("link_record_ids"), list):
            return [str(x) for x in v["link_record_ids"]]
        if v.get("id"):
            return [str(v["id"])]
        return res
    if isinstance(v, list):
        for x in v:
            res.extend(ids_of(x))
    elif isinstance(v, str) and v.strip():
        res.append(v.strip())
    return res


def to_date(v):
    s = txt(v) if not isinstance(v, str) else v
    s = s.strip()
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    if re.fullmatch(r"\d{10,13}", s):
        ts = int(s) / (1000 if len(s) == 13 else 1)
        return datetime.fromtimestamp(ts).date()
    return None


def status_of(v):
    s = txt(v)
    return s


# ---------------------------------------------------------------- 领域模型

INACTIVE_STATUS = {"停用"}
DIRECT_COST_TYPES = {"柴油", "维修", "配件", "司机工资", "过路费", "吊索具", "其他"}
UNPAID_STATUS = {"未结算", "部分结算", "挂账"}


class Book:
    def __init__(self, eq_rows, cu_rows, sh_rows, pay_rows, cost_rows):
        self.eq = self._build_eq(eq_rows)
        self.cu = self._build_cu(cu_rows)
        self.sh = self._build_sh(sh_rows)
        self.pay = self._build_pay(pay_rows)
        self.cost = self._build_cost(cost_rows)

    # --- 设备
    def _build_eq(self, rows):
        out = []
        for r in rows:
            out.append({
                "id": r.get("_id"),
                "code": txt(r.get("设备编号")) or txt(r.get("设备名称")),
                "name": txt(r.get("设备名称")) or txt(r.get("设备编号")),
                "type": txt(r.get("设备类型")) or "未分类",
                "ton": txt(r.get("吨位档")) or "未填吨位",
                "price": num(r.get("台班单价")),
                "ot_price": num(r.get("加班小时单价")),
                "status": txt(r.get("设备状态")) or "未知",
                "owner": txt(r.get("归属方式")) or "自有",
                "insurance": to_date(r.get("保险到期日")),
                "inspection": to_date(r.get("年检到期日")),
            })
        return out

    # --- 客户
    def _build_cu(self, rows):
        out = []
        for r in rows:
            out.append({
                "id": r.get("_id"),
                "name": txt(r.get("客户名称")),
                "type": txt(r.get("客户类型")),
                "project": txt(r.get("项目名称")),
                "credit": num(r.get("账期天数")),
                "status": txt(r.get("合作状态")),
            })
        return out

    # --- 台班
    def _build_sh(self, rows):
        out = []
        for r in rows:
            d = to_date(r.get("日期"))
            qty = num(r.get("台班数"))
            price = num(r.get("台班单价"))
            ot = num(r.get("加班小时"))
            otp = num(r.get("加班单价"))
            rev = num(r.get("收入金额"))
            if not rev:
                rev = qty * price + ot * otp
            recv_field = "待收金额" in r
            recv = num(r.get("待收金额")) if recv_field else None
            st = txt(r.get("结算状态"))
            if recv is None:
                recv = 0.0 if st == "已结算" else rev
            out.append({
                "date": d,
                "eq_ids": ids_of(r.get("关联设备")),
                "cu_ids": ids_of(r.get("关联客户")),
                "site": txt(r.get("项目工地")),
                "content": txt(r.get("作业内容")),
                "stype": txt(r.get("台班类型")),
                "qty": qty,
                "ot": ot,
                "price": price,
                "rev": rev,
                "recv": recv,
                "status": st,
                "sales": txt(r.get("业务员")),
                "driver": txt(r.get("司机")),
            })
        return [x for x in out if x["date"]]

    def _build_pay(self, rows):
        out = []
        for r in rows:
            d = to_date(r.get("回款日期"))
            if not d:
                continue
            out.append({"date": d, "cu_ids": ids_of(r.get("关联客户")),
                        "amount": num(r.get("回款金额")), "way": txt(r.get("回款方式"))})
        return out

    def _build_cost(self, rows):
        out = []
        for r in rows:
            d = to_date(r.get("发生日期"))
            if not d:
                continue
            out.append({"date": d, "eq_ids": ids_of(r.get("关联设备")),
                        "type": txt(r.get("费用类型")) or "其他", "amount": num(r.get("金额"))})
        return out

    # --- 索引
    def eq_by_id(self, rid):
        for e in self.eq:
            if e["id"] == rid:
                return e
        return None

    def cu_by_id(self, rid):
        for c in self.cu:
            if c["id"] == rid:
                return c
        return None

    def eq_of(self, sh):
        """一条台班的主设备（多设备时取第一个）"""
        for rid in sh["eq_ids"]:
            e = self.eq_by_id(rid)
            if e:
                return e
        return None

    def cu_of(self, sh):
        for rid in sh["cu_ids"]:
            c = self.cu_by_id(rid)
            if c:
                return c
        return None


# ---------------------------------------------------------------- 单日汇总


def day_snapshot(book, d):
    shifts = [s for s in book.sh if s["date"] == d]
    pays = [p for p in book.pay if p["date"] == d]
    costs = [c for c in book.cost if c["date"] == d]

    qty = sum(s["qty"] for s in shifts)
    rev = sum(s["rev"] for s in shifts)
    cash = sum(p["amount"] for p in pays)

    direct = sum(c["amount"] for c in costs if c["type"] in DIRECT_COST_TYPES)
    cost_total = sum(c["amount"] for c in costs)

    active = {e["id"] for e in book.eq if e["status"] not in INACTIVE_STATUS}
    attended = set()
    by_type = defaultdict(lambda: {"qty": 0.0, "rev": 0.0, "eq": set(), "eqs": []})
    by_eq = defaultdict(lambda: {"qty": 0.0, "rev": 0.0, "cost": 0.0})
    by_cu = defaultdict(lambda: {"qty": 0.0, "rev": 0.0, "cash": 0.0})
    by_sales = defaultdict(lambda: {"qty": 0.0, "rev": 0.0})
    by_site = defaultdict(lambda: {"qty": 0.0, "rev": 0.0})
    by_status = defaultdict(lambda: {"cnt": 0, "rev": 0.0})
    unlinked_rev = 0.0
    unlinked_cnt = 0
    no_sales_cnt = 0
    ext_rev = 0.0

    for s in shifts:
        if not s["sales"]:
            no_sales_cnt += 1
        st = s["status"] or "未填结算状态"
        by_status[st]["cnt"] += 1
        by_status[st]["rev"] += s["rev"]

        e = book.eq_of(s)
        if e:
            attended.add(e["id"])
            key = (e["type"], e["ton"])
            by_type[key]["qty"] += s["qty"]
            by_type[key]["rev"] += s["rev"]
            by_type[key]["eq"].add(e["id"])
            by_eq[e["code"]]["qty"] += s["qty"]
            by_eq[e["code"]]["rev"] += s["rev"]
            if e["owner"] == "外协":
                ext_rev += s["rev"]
        else:
            unlinked_rev += s["rev"]
            unlinked_cnt += 1
            by_eq["未关联设备的台班"]["qty"] += s["qty"]
            by_eq["未关联设备的台班"]["rev"] += s["rev"]

        c = book.cu_of(s)
        cu_name = c["name"] if c else (s["site"] or "未填客户")
        by_cu[cu_name]["qty"] += s["qty"]
        by_cu[cu_name]["rev"] += s["rev"]
        by_sales[s["sales"] or "未指定"]["qty"] += s["qty"]
        by_sales[s["sales"] or "未指定"]["rev"] += s["rev"]
        site = s["site"] or (c["project"] if c else "") or "未填工地"
        by_site[site]["qty"] += s["qty"]
        by_site[site]["rev"] += s["rev"]

    for p in pays:
        c = None
        for rid in p["cu_ids"]:
            c = book.cu_by_id(rid)
            if c:
                break
        by_cu[c["name"] if c else "未填客户"]["cash"] += p["amount"]

    by_cost_type = defaultdict(float)
    for c in costs:
        by_cost_type[c["type"]] += c["amount"]
        for rid in c["eq_ids"]:
            e = book.eq_by_id(rid)
            if e:
                by_eq[e["code"]]["cost"] += c["amount"]

    gp = rev - direct
    # 当日没有成本记录时毛利率无意义，留空而不是显示 100%
    margin = (gp / rev * 100) if (rev and costs) else None
    rate = (len(attended) / len(active) * 100) if active else None

    return {
        "date": d.isoformat(),
        "shift_count": len(shifts),
        "qty": qty,
        "rev": rev,
        "cash": cash,
        "direct_cost": direct,
        "cost_total": cost_total,
        "gross": gp,
        "margin": margin,
        "attended": len(attended),
        "active": len(active),
        "rate": rate,
        "by_type": by_type,
        "by_eq": by_eq,
        "by_cu": by_cu,
        "by_sales": by_sales,
        "by_site": by_site,
        "by_status": by_status,
        "by_cost_type": by_cost_type,
        "unlinked_rev": unlinked_rev,
        "unlinked_cnt": unlinked_cnt,
        "no_sales_cnt": no_sales_cnt,
        "ext_rev": ext_rev,
        "attended_ids": attended,
        "shift_rows": shifts,
    }


def receivable_book(book, today):
    """应收余额 + 账龄（按客户）"""
    aging = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    by_cu = defaultdict(float)
    overdue = []
    overdue_total = 0.0
    for s in book.sh:
        if s["status"] not in UNPAID_STATUS:
            continue
        amt = s["recv"]
        if amt <= 0:
            continue
        c = book.cu_of(s)
        cname = c["name"] if c else (s["site"] or "未填客户")
        by_cu[cname] += amt
        days = (today - s["date"]).days
        bucket = "0-30" if days <= 30 else "31-60" if days <= 60 else "61-90" if days <= 90 else "90+"
        aging[bucket] += amt
        if c and days > c["credit"]:
            overdue.append({"customer": cname, "amount": amt, "days": days,
                            "credit": c["credit"], "date": s["date"].isoformat()})
    for o in overdue:
        overdue_total += o["amount"]
    return {"by_customer": by_cu, "aging": aging, "overdue": overdue,
            "overdue_total": overdue_total, "total": sum(by_cu.values())}


# ---------------------------------------------------------------- 预警


def build_warnings(book, snap, recv, today):
    red, yellow = [], []

    for o in recv["overdue"]:
        if o["amount"] >= 5000:
            red.append(f"超期应收：{o['customer']} 欠 ¥{o['amount']:,.0f}，账龄 {o['days']} 天（账期 {o['credit']:.0f} 天，{o['date']} 台班）")

    for e in book.eq:
        for label, dt in (("保险", e["insurance"]), ("年检", e["inspection"])):
            if not dt:
                continue
            left = (dt - today).days
            if left <= 15:
                state = "已过期" if left < 0 else f"仅剩 {left} 天"
                red.append(f"证照到期：{e['code']}（{e['name']}）{label} {dt.isoformat()}，{state}")

    for code, v in snap["by_eq"].items():
        if v["rev"] > 0 and v["cost"] > v["rev"]:
            yellow.append(f"单机毛利为负：{code} 产值 ¥{v['rev']:,.0f}、成本 ¥{v['cost']:,.0f}，倒挂 ¥{v['cost'] - v['rev']:,.0f}")

    # 连续零出勤（待租设备）
    last = {}
    for s in book.sh:
        for e in book.eq:
            if e["id"] in s["eq_ids"]:
                last[e["code"]] = max(last.get(e["code"], date.min), s["date"])
    for e in book.eq:
        if e["status"] != "待租":
            continue
        if e["id"] in snap["attended_ids"]:
            continue
        if e["code"] in snap["by_eq"]:
            continue
        ldt = last.get(e["code"])
        gap = (today - ldt).days if ldt else 999
        if ldt and gap < 3:
            continue  # 连续满 3 天零台班才算闲置
        tail = f"已 {gap} 天无台班" if ldt else "从未出过台班"
        yellow.append(f"闲置：{e['code']}（{e['name']}）状态待租，{tail}")

    stale = 0
    for s in book.sh:
        if s["status"] in UNPAID_STATUS and (today - s["date"]).days > 30:
            stale += 1
    if stale:
        yellow.append(f"未结算积压：{stale} 条台班超过 30 天未结算")

    if snap["no_sales_cnt"]:
        yellow.append(f"业务员缺失：今日 {snap['no_sales_cnt']} 条台班未填业务员")

    if snap["rev"] > 0:
        top_cu = max(snap["by_cu"].items(), key=lambda kv: kv[1]["rev"])
        share = top_cu[1]["rev"] / snap["rev"] * 100
        if share > 50:
            yellow.append(f"客户集中：{top_cu[0]} 占今日产值 {share:.0f}%")

    if snap["rev"] > 0 and snap["ext_rev"] / snap["rev"] * 100 > 40:
        yellow.append(f"外协依赖：外协设备占今日产值 {snap['ext_rev'] / snap['rev'] * 100:.0f}%")

    if snap["rate"] is not None and snap["active"] >= 5 and snap["rate"] < 60:
        yellow.append(f"出勤率偏低：{snap['rate']:.0f}%（在册 {snap['active']} 台，出勤 {snap['attended']} 台）")

    if snap["unlinked_cnt"]:
        yellow.append(f"设备未上台账：{snap['unlinked_cnt']} 条台班未关联设备，产值 ¥{snap['unlinked_rev']:,.0f}")
    return red, yellow


# ---------------------------------------------------------------- 渲染


def money(v, dec=0):
    if v is None:
        return "—"
    if dec:
        return f"¥{v:,.{dec}f}"
    return f"¥{v:,.0f}"


def pct(v, dec=1):
    return "—" if v is None else f"{v:.{dec}f}%"


def delta(cur, prev):
    if prev is None or prev == 0:
        return "—"
    return f"{(cur - prev) / prev * 100:+.1f}%"


def pp(cur, prev):
    if cur is None or prev is None:
        return "—"
    return f"{cur - prev:+.1f}pp"


WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def render(book, d, snap, prev, week, recv, red, yellow):
    S = snap
    lines = []
    A = lines.append

    A(f"# 经营日报 | {d.isoformat()}（{WEEKDAYS[d.weekday()]}）")
    A("")

    head = (f"**一句话**：今日台班 **{S['qty']:.1f} 个**、产值 **{money(S['rev'])}**"
            f"（日环比 {delta(S['rev'], prev['rev'])}）、回款 **{money(S['cash'])}**、"
            f"出勤 **{S['attended']}/{S['active']} 台**（{pct(S['rate'])}），"
            f"毛利 **{money(S['gross'])}**（{pct(S['margin'])}）。")
    A(head)
    A("")

    # 一、核心指标
    A("## 一、核心指标")
    A("")
    A("| 指标 | 今日 | 昨日 | 上周同日 | 日环比 | 周同比 |")
    A("|---|---|---|---|---|---|")
    A(f"| 台班数(个) | {S['qty']:.1f} | {prev['qty']:.1f} | {week['qty']:.1f} | {delta(S['qty'], prev['qty'])} | {delta(S['qty'], week['qty'])} |")
    A(f"| 产值(元) | {S['rev']:,.0f} | {prev['rev']:,.0f} | {week['rev']:,.0f} | {delta(S['rev'], prev['rev'])} | {delta(S['rev'], week['rev'])} |")
    A(f"| 回款(元) | {S['cash']:,.0f} | {prev['cash']:,.0f} | {week['cash']:,.0f} | {delta(S['cash'], prev['cash'])} | {delta(S['cash'], week['cash'])} |")
    A(f"| 出勤设备(台) | {S['attended']}/{S['active']} | {prev['attended']}/{prev['active']} | {week['attended']}/{week['active']} | — | — |")
    A(f"| 出勤率 | {pct(S['rate'])} | {pct(prev['rate'])} | {pct(week['rate'])} | {pp(S['rate'], prev['rate'])} | {pp(S['rate'], week['rate'])} |")
    A(f"| 直接成本(元) | {S['direct_cost']:,.0f} | {prev['direct_cost']:,.0f} | {week['direct_cost']:,.0f} | {delta(S['direct_cost'], prev['direct_cost'])} | {delta(S['direct_cost'], week['direct_cost'])} |")
    A(f"| 毛利(元) | {S['gross']:,.0f} | {prev['gross']:,.0f} | {week['gross']:,.0f} | {delta(S['gross'], prev['gross'])} | {delta(S['gross'], week['gross'])} |")
    A(f"| 毛利率 | {pct(S['margin'])} | {pct(prev['margin'])} | {pct(week['margin'])} | {pp(S['margin'], prev['margin'])} | {pp(S['margin'], week['margin'])} |")
    A("")

    # 二、设备与吨位
    A("## 二、设备与吨位维度")
    A("")
    if S["by_type"]:
        A("| 设备类型 | 吨位档 | 台班 | 产值 | 占产值比 | 出勤台数 |")
        A("|---|---|---|---|---|---|")
        for (t, ton), v in sorted(S["by_type"].items(), key=lambda kv: -kv[1]["rev"]):
            share = v["rev"] / S["rev"] * 100 if S["rev"] else None
            A(f"| {t} | {ton} | {v['qty']:.1f} | {money(v['rev'])} | {pct(share)} | {len(v['eq'])} |")
        A("")
        crane_rev = sum(v["rev"] for (t, _), v in S["by_type"].items() if t in ("汽车吊", "履带吊", "随车吊"))
        truck_rev = sum(v["rev"] for (t, _), v in S["by_type"].items() if t in ("平板车", "低平板", "高栏车"))
        A(f"- 吊机产值 {money(crane_rev)}（{pct(crane_rev / S['rev'] * 100 if S['rev'] else None)}），"
          f"平板车产值 {money(truck_rev)}（{pct(truck_rev / S['rev'] * 100 if S['rev'] else None)}）。")
    else:
        A("今日无台班记录。")
    A("")

    # 三、单台设备
    A("## 三、单台设备")
    A("")
    tops = sorted([(k, v) for k, v in S["by_eq"].items() if v["rev"] > 0],
                  key=lambda kv: -kv[1]["rev"])[:5]
    if tops:
        A("**产值 Top 5**")
        A("")
        A("| 设备 | 台班 | 产值 | 当日成本 | 单机毛利 |")
        A("|---|---|---|---|---|")
        for code, v in tops:
            A(f"| {code} | {v['qty']:.1f} | {money(v['rev'])} | {money(v['cost'])} | {money(v['rev'] - v['cost'])} |")
        A("")

    idle = [e for e in book.eq
            if e["status"] != "停用" and e["id"] not in S["attended_ids"] and e["code"] not in S["by_eq"]]
    if idle:
        A("**今日零出勤设备**")
        A("")
        A("| 设备 | 名称 | 状态 | 归属 | 档位 |")
        A("|---|---|---|---|---|")
        for e in idle:
            A(f"| {e['code']} | {e['name']} | {e['status']} | {e['owner']} | {e['type']}/{e['ton']} |")
        A("")

    # 四、客户与项目
    A("## 四、客户与项目维度")
    A("")
    if S["by_cu"]:
        A("| 客户 | 台班 | 今日产值 | 今日回款 | 应收余额 | 占产值比 |")
        A("|---|---|---|---|---|---|")
        cur_recv = recv["by_customer"]
        for name, v in sorted(S["by_cu"].items(), key=lambda kv: -kv[1]["rev"]):
            share = v["rev"] / S["rev"] * 100 if S["rev"] else None
            A(f"| {name} | {v['qty']:.1f} | {money(v['rev'])} | {money(v['cash'])} | "
              f"{money(cur_recv.get(name, 0))} | {pct(share)} |")
        A("")

    if S["by_site"]:
        A("**按工地**：" + "；".join(
            f"{k} {money(v['rev'])}" for k, v in sorted(S["by_site"].items(), key=lambda kv: -kv[1]["rev"])[:5]))
        A("")

    # 五、业务员
    A("## 五、业务员维度")
    A("")
    if S["by_sales"]:
        A("| 业务员 | 台班 | 产值 | 占产值比 |")
        A("|---|---|---|---|")
        for name, v in sorted(S["by_sales"].items(), key=lambda kv: -kv[1]["rev"]):
            share = v["rev"] / S["rev"] * 100 if S["rev"] else None
            A(f"| {name} | {v['qty']:.1f} | {money(v['rev'])} | {pct(share)} |")
        A("")

    # 六、结算与应收
    A("## 六、结算与应收")
    A("")
    A("**今日台班的结算状态**")
    A("")
    A("| 结算状态 | 笔数 | 金额 | 占产值比 |")
    A("|---|---|---|---|")
    for st, v in sorted(S["by_status"].items(), key=lambda kv: -kv[1]["rev"]):
        share = v["rev"] / S["rev"] * 100 if S["rev"] else None
        A(f"| {st} | {v['cnt']} | {money(v['rev'])} | {pct(share)} |")
    A("")
    A(f"**应收余额合计 {money(recv['total'])}**，其中超期 {money(recv['overdue_total'])}。")
    A("")
    A("| 账龄 | 金额 |")
    A("|---|---|")
    for k in ("0-30", "31-60", "61-90", "90+"):
        A(f"| {k} 天 | {money(recv['aging'][k])} |")
    A("")
    if recv["overdue"]:
        A("| 超期客户 | 欠款 | 账龄 | 账期 |")
        A("|---|---|---|---|")
        for o in sorted(recv["overdue"], key=lambda x: -x["amount"]):
            A(f"| {o['customer']} | {money(o['amount'])} | {o['days']} 天 | {o['credit']:.0f} 天 |")
        A("")

    # 七、成本
    A("## 七、成本与毛利")
    A("")
    if S["by_cost_type"]:
        A("| 费用类型 | 金额 | 占成本比 |")
        A("|---|---|---|")
        for k, v in sorted(S["by_cost_type"].items(), key=lambda kv: -kv[1]):
            share = v / S["direct_cost"] * 100 if S["direct_cost"] else None
            tag = "" if k in DIRECT_COST_TYPES else "（不计入直接成本）"
            A(f"| {k}{tag} | {money(v)} | {pct(share)} |")
        A("")
        A(f"直接成本 {money(S['direct_cost'])}，毛利 {money(S['gross'])}，毛利率 {pct(S['margin'])}。")
    else:
        A("今日未录入成本。毛利按「产值 − 0」计算，仅供参考。")
    A("")

    # 八、预警
    A("## 八、预警")
    A("")
    if red or yellow:
        for r in red:
            A(f"- 🔴 {r}")
        for y in yellow:
            A(f"- 🟡 {y}")
    else:
        A("今日无预警。")
    A("")

    # 九、明日待办
    A("## 九、明日待办")
    A("")
    todos = []
    for o in sorted(recv["overdue"], key=lambda x: -x["amount"])[:2]:
        todos.append(f"催收：{o['customer']} ¥{o['amount']:,.0f}（已逾期 {o['days'] - o['credit']:.0f} 天）")
    for e in book.eq:
        for label, dt in (("保险", e["insurance"]), ("年检", e["inspection"])):
            if dt and 0 <= (dt - d).days <= 15:
                todos.append(f"{e['code']} {label} {dt.isoformat()} 到期，安排续办")
                break
    for e in idle:
        if e["status"] == "待租":
            todos.append(f"{e['code']}（{e['type']}/{e['ton']}）待租，联系客户派车")
            break
    if not todos:
        todos.append("无待办事项，按常规排班。")
    for t in todos[:5]:
        A(f"- {t}")
    A("")

    # 十、口径
    A("## 十、口径与完整性")
    A("")
    A("| 项 | 说明 |")
    A("|---|---|")
    A(f"| 统计日 | {d.isoformat()}（{WEEKDAYS[d.weekday()]}） |")
    A(f"| 数据量 | 台班 {len(book.sh)} 条 / 回款 {len(book.pay)} 条 / 成本 {len(book.cost)} 条 / 设备 {len(book.eq)} 台 / 客户 {len(book.cu)} 个 |")
    A("| 产值 | Σ(台班数×台班单价 + 加班小时×加班单价) |")
    A("| 出勤率 | 当日有台班设备数 ÷ 在册设备数（不含停用） |")
    A("| 直接成本 | 柴油/维修/配件/司机工资/过路费/吊索具/其他；保险、年检不计入 |")
    A("| 应收 | 未结算+部分结算+挂账 的待收金额合计（部分结算按未收全额，保守口径） |")
    A("| 缺失 | 未录入的表按 0 计，不做估算 |")
    if S["unlinked_cnt"]:
        A(f"| 异常 | {S['unlinked_cnt']} 条台班未关联设备，产值 {money(S['unlinked_rev'])} 未计入设备维度 |")
    A("")

    return "\n".join(lines)


# ---------------------------------------------------------------- 主流程


def main():
    ap = argparse.ArgumentParser(description="机械租赁经营日报")
    ap.add_argument("--date", required=False, help="统计日期 YYYY-MM-DD，默认今天")
    ap.add_argument("--shifts", nargs="*", default=[], help="台班记录导出 JSON（可多个）")
    ap.add_argument("--equipment", nargs="*", default=[], help="设备台账导出 JSON")
    ap.add_argument("--customers", nargs="*", default=[], help="客户与项目导出 JSON")
    ap.add_argument("--payments", nargs="*", default=[], help="回款记录导出 JSON")
    ap.add_argument("--costs", nargs="*", default=[], help="成本支出导出 JSON")
    ap.add_argument("--out", help="日报 Markdown 输出路径")
    ap.add_argument("--json-out", help="指标 JSON 输出路径")
    a = ap.parse_args()

    d = date.today()
    if a.date:
        m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", a.date)
        if not m:
            print("--date 需要 YYYY-MM-DD", file=sys.stderr)
            return 2
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    sh = load_table(a.shifts)
    if not sh:
        print("没有读到台班记录：先用 lark-cli base +record-list --format json 导出 --shifts", file=sys.stderr)
        return 2

    book = Book(load_table(a.equipment), load_table(a.customers), sh,
                load_table(a.payments), load_table(a.costs))

    snap = day_snapshot(book, d)
    prev = day_snapshot(book, d - timedelta(days=1))
    week = day_snapshot(book, d - timedelta(days=7))
    recv = receivable_book(book, d)
    red, yellow = build_warnings(book, snap, recv, d)

    md = render(book, d, snap, prev, week, recv, red, yellow)

    metrics = {
        "date": d.isoformat(),
        "qty": round(snap["qty"], 2),
        "rev": round(snap["rev"], 2),
        "cash": round(snap["cash"], 2),
        "direct_cost": round(snap["direct_cost"], 2),
        "gross": round(snap["gross"], 2),
        "margin": None if snap["margin"] is None else round(snap["margin"], 2),
        "attended": snap["attended"],
        "active": snap["active"],
        "rate": None if snap["rate"] is None else round(snap["rate"], 2),
        "receivable_total": round(recv["total"], 2),
        "overdue_total": round(recv["overdue_total"], 2),
        "by_type": {f"{k[0]}/{k[1]}": round(v["rev"], 2) for k, v in snap["by_type"].items()},
        "by_customer": {k: round(v["rev"], 2) for k, v in snap["by_cu"].items()},
        "by_sales": {k: round(v["rev"], 2) for k, v in snap["by_sales"].items()},
        "warning_red": len(red),
        "warning_yellow": len(yellow),
        "warnings": red + yellow,
    }

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(md)
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
