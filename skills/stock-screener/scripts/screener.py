#!/usr/bin/env python3
"""
Stock Screener — 多因子选股器 v1.0.0

连接 fund-flow / market-signals → stock-planner 的桥梁。
支持技术面/资金面/基本面多条件筛选、综合评分排序、单股明细分析。

Usage:
  python3 scripts/screener.py filter   --file stocks.csv [--rsi-min 30] [--rsi-max 70] ...
  python3 scripts/screener.py rank     --file stocks.csv [--weight-tech 0.4]
  python3 scripts/screener.py score    --file stocks.csv --code 600519
  python3 scripts/screener.py summary  --file stocks.csv
  python3 scripts/screener.py correlation --file stocks.csv
"""

import argparse
import csv
import json
import math
import os
import sys
from collections import OrderedDict

# ─── 免责声明 ────────────────────────────────────────────
DISCLAIMER = (
    "\n⚠️  免责声明：本工具仅作为辅助参考，不构成任何投资建议。"
    "\n    所有数据来源于用户输入，筛选结果仅供进一步分析使用。"
    "\n    投资有风险，入市需谨慎。过往表现不代表未来收益。\n"
)

# ─── 列名自动识别 ────────────────────────────────────────

COLUMN_ALIASES = {
    "code":     ["code", "stock", "symbol", "代码", "股票代码", "ts_code"],
    "name":     ["name", "名称", "股票名称", "stock_name"],
    "price":    ["price", "close", "现价", "收盘价", "current_price"],
    "rsi":      ["rsi", "RSI", "rsi_14"],
    "ma_signal": ["ma_signal", "ma_sign", "ma_sig", "MA信号", "ma_signal_name"],
    "volume_ratio": ["volume_ratio", "vol_ratio", "量比", "volume_ratio_pct"],
    "main_flow": ["main_flow", "main_force", "fundflow", "主力净流入", "fund_flow", "net_main_inflow"],
    "pe":       ["pe", "PE", "市盈率", "pe_ttm"],
    "pb":       ["pb", "PB", "市净率", "pb_lf"],
    "market_cap": ["market_cap", "mcap", "市值", "总市值", "capital", "total_mv"],
    "change_pct": ["change_pct", "change", "涨跌幅", "pct_chg", "pct_change", "change_percent"],
    "high":     ["high", "最高", "high_price"],
    "low":      ["low", "最低", "low_price"],
    "volume":   ["volume", "vol", "成交量", "amount", "成交额"],
}


def resolve_columns(headers):
    """将CSV表头映射到标准化列名。"""
    header_lower = {h.strip().lower(): h.strip() for h in headers}
    mapping = {}
    for std_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_lower = alias.lower()
            if alias_lower in header_lower:
                mapping[std_name] = header_lower[alias_lower]
                break
    return mapping


# ─── 数据加载 ────────────────────────────────────────────

def load_csv(filepath):
    """加载CSV文件，返回(rows, column_mapping)。"""
    if not os.path.isfile(filepath):
        print(f"错误: 文件不存在: {filepath}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            rows = list(reader)
    except Exception as e:
        print(f"错误: 无法读取CSV: {e}", file=sys.stderr)
        sys.exit(1)
    if not rows:
        print("错误: CSV文件为空", file=sys.stderr)
        sys.exit(1)
    col_map = resolve_columns(headers)
    return rows, col_map, headers


def safe_float(val):
    """安全转浮点，失败返回None。"""
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(str(val).replace(",", "").replace(" ", ""))
    except (ValueError, TypeError):
        return None


def safe_int(val):
    """安全转整数，失败返回None。"""
    f = safe_float(val)
    return int(f) if f is not None else None


# ─── 筛选逻辑 ────────────────────────────────────────────

def _filter_row(row, col_map, args):
    """单行筛选条件检查，返回True表示通过。"""
    # RSI 范围
    if args.rsi_min is not None or args.rsi_max is not None:
        rsi = safe_float(row.get(col_map.get("rsi", "")))
        if rsi is not None:
            if args.rsi_min is not None and rsi < args.rsi_min:
                return False
            if args.rsi_max is not None and rsi > args.rsi_max:
                return False
        # 如果列不存在，跳过此条件

    # 均线信号
    if args.ma_signal:
        sig_col = col_map.get("ma_signal")
        if sig_col:
            val = row.get(sig_col, "").strip().lower()
            target = args.ma_signal.lower()
            if val != target:
                return False

    # 量比
    if args.volume_ratio_min is not None:
        vr = safe_float(row.get(col_map.get("volume_ratio", "")))
        if vr is not None and vr < args.volume_ratio_min:
            return False

    # 资金净流入
    if args.fundflow_min is not None:
        ff = safe_float(row.get(col_map.get("main_flow", "")))
        if ff is not None and ff < args.fundflow_min:
            return False

    # PE
    if args.pe_min is not None or args.pe_max is not None:
        pe = safe_float(row.get(col_map.get("pe", "")))
        if pe is not None and pe > 0:
            if args.pe_min is not None and pe < args.pe_min:
                return False
            if args.pe_max is not None and pe > args.pe_max:
                return False

    # PB
    if args.pb_min is not None or args.pb_max is not None:
        pb = safe_float(row.get(col_map.get("pb", "")))
        if pb is not None and pb > 0:
            if args.pb_min is not None and pb < args.pb_min:
                return False
            if args.pb_max is not None and pb > args.pb_max:
                return False

    # 价格
    if args.price_min is not None or args.price_max is not None:
        p = safe_float(row.get(col_map.get("price", "")))
        if p is not None:
            if args.price_min is not None and p < args.price_min:
                return False
            if args.price_max is not None and p > args.price_max:
                return False

    # 市值
    if args.market_cap_min is not None or args.market_cap_max is not None:
        mc = safe_float(row.get(col_map.get("market_cap", "")))
        if mc is not None:
            if args.market_cap_min is not None and mc < args.market_cap_min:
                return False
            if args.market_cap_max is not None and mc > args.market_cap_max:
                return False

    # 涨跌幅
    if args.change_min is not None or args.change_max is not None:
        ch = safe_float(row.get(col_map.get("change_pct", "")))
        if ch is not None:
            if args.change_min is not None and ch < args.change_min:
                return False
            if args.change_max is not None and ch > args.change_max:
                return False

    return True


def cmd_filter(rows, col_map, headers, args):
    """多条件筛选股票。"""
    filtered = [r for r in rows if _filter_row(r, col_map, args)]
    print(f"筛选结果: {len(filtered)} / {len(rows)} 只股票通过条件\n")

    if not filtered:
        print("未找到符合条件的股票。")
        return

    # 显示摘要表格
    name_col = col_map.get("name", "")
    code_col = col_map.get("code", "")
    price_col = col_map.get("price", "")
    change_col = col_map.get("change_pct", "")

    print(f"{'序号':<4} {'代码':<10} {'名称':<12} {'现价':<10} {'涨跌幅':<10}")
    print("-" * 50)
    for i, row in enumerate(filtered, 1):
        code = row.get(code_col, "") if code_col else ""
        name = row.get(name_col, "") if name_col else ""
        price = row.get(price_col, "") if price_col else ""
        chg = row.get(change_col, "") if change_col else ""
        print(f"{i:<4} {code:<10} {name:<12} {price:<10} {chg:<10}")

    # 输出文件
    if args.output:
        if not filtered:
            return
        out_cols = headers
        try:
            with open(args.output, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=out_cols)
                writer.writeheader()
                writer.writerows(filtered)
            print(f"\n结果已保存: {args.output}")
        except Exception as e:
            print(f"错误: 保存文件失败: {e}", file=sys.stderr)


# ─── 综合评分 ────────────────────────────────────────────

def _normalize(values, reverse=False):
    """最小-最大归一化到 0-100。"""
    vals = [v for v in values if v is not None and (v >= 0 if v is not None else True)]
    if not vals:
        return {i: 50.0 for i in range(len(values))}

    # 对于PE/PB，处理异常值
    if not reverse:
        # 去除前5%极端值
        sorted_vals = sorted(vals)
        n = len(sorted_vals)
        if n >= 3:
            trim = max(1, n // 20)
            trimmed = sorted_vals[trim:-trim] if trim * 2 < n else sorted_vals
        else:
            trimmed = sorted_vals
        mn, mx = min(trimmed), max(trimmed)
    else:
        mn, mx = min(vals), max(vals)

    if mx == mn:
        return {i: 50.0 for i in range(len(values))}

    result = {}
    for i, v in enumerate(values):
        if v is None:
            result[i] = 50.0  # 缺失默认中位
        else:
            raw = ((v - mn) / (mx - mn)) * 100
            result[i] = raw if not reverse else 100 - raw
    return result


def _score_rsi(rsi):
    """RSI评分：30-70为中性，<30超卖加分，>70超买减分。"""
    if rsi is None:
        return 50
    if rsi < 30:
        return min(100, 50 + (30 - rsi) * 2.5)  # 超卖，看多信号
    elif rsi > 70:
        return max(0, 50 - (rsi - 70) * 2.5)    # 超买，看空信号
    elif rsi < 50:
        return 50 + (50 - rsi) * 0.8  # 偏弱但可接受
    else:
        return 50 - (rsi - 50) * 0.8  # 偏强但可接受


def _score_ma_signal(signal):
    """均线信号评分。"""
    s = str(signal).strip().lower() if signal else ""
    scores = {
        "bullish": 85, "金叉": 85, "多头": 85, "买入": 85,
        "bearish": 15, "死叉": 15, "空头": 15, "卖出": 15,
        "cross": 75, "cross_up": 80, "cross_down": 20,
    }
    return scores.get(s, 50)


def _score_volume_ratio(vr):
    """量比评分：>1.5放量加分。"""
    if vr is None:
        return 50
    if vr > 2.0:
        return min(100, 50 + (vr - 2.0) * 20)
    elif vr > 1.5:
        return 65
    elif vr > 1.0:
        return 55
    elif vr > 0.5:
        return 45
    else:
        return 30


def _score_main_flow(flow, all_flows):
    """主力资金评分：基于全体排名。"""
    if flow is None:
        return 50
    if not all_flows:
        return 50 if flow >= 0 else 30
    # 计算在全体中的百分位
    positive = sum(1 for f in all_flows if f is not None and f < flow)
    total = sum(1 for f in all_flows if f is not None)
    if total == 0:
        return 50
    percentile = positive / total * 100
    return percentile


def _score_pe(pe):
    """PE评分：低PE加分，高PE减分。"""
    if pe is None or pe <= 0:
        return 50
    if pe < 10:
        return 85
    elif pe < 20:
        return 75
    elif pe < 30:
        return 60
    elif pe < 50:
        return 45
    elif pe < 100:
        return 30
    else:
        return 15


def _score_pb(pb):
    """PB评分：低PB加分。"""
    if pb is None or pb <= 0:
        return 50
    if pb < 1:
        return 90
    elif pb < 2:
        return 75
    elif pb < 3:
        return 60
    elif pb < 5:
        return 45
    elif pb < 10:
        return 30
    else:
        return 15


def _score_change_pct(chg):
    """涨跌幅评分：温和上涨最佳。"""
    if chg is None:
        return 50
    if -1 <= chg <= 1:
        return 50
    elif 1 < chg <= 3:
        return 65
    elif 3 < chg <= 5:
        return 70
    elif 5 < chg <= 10:
        return 60
    elif chg > 10:
        return 50
    elif -3 <= chg < -1:
        return 40
    elif -5 <= chg < -3:
        return 30
    else:
        return 20


def compute_scores(rows, col_map, w_tech=0.4, w_fund=0.3, w_basic=0.3):
    """计算每只股票的综合评分。"""
    total_w = w_tech + w_fund + w_basic
    if total_w <= 0:
        w_tech, w_fund, w_basic = 0.4, 0.3, 0.3
    else:
        w_tech /= total_w
        w_fund /= total_w
        w_basic /= total_w

    all_flows = [safe_float(r.get(col_map.get("main_flow", ""))) for r in rows]

    results = []
    for row in rows:
        rsi = safe_float(row.get(col_map.get("rsi", "")))
        ma_sig = row.get(col_map.get("ma_signal", ""))
        vr = safe_float(row.get(col_map.get("volume_ratio", "")))
        flow = safe_float(row.get(col_map.get("main_flow", "")))
        pe = safe_float(row.get(col_map.get("pe", "")))
        pb = safe_float(row.get(col_map.get("pb", "")))
        chg = safe_float(row.get(col_map.get("change_pct", "")))

        # 技术面评分 (40%)
        s_rsi = _score_rsi(rsi)
        s_ma = _score_ma_signal(ma_sig)
        s_vr = _score_volume_ratio(vr)
        tech_score = s_rsi * 0.35 + s_ma * 0.35 + s_vr * 0.30

        # 资金面评分 (30%)
        fund_score = _score_main_flow(flow, all_flows)

        # 基本面评分 (30%)
        s_pe = _score_pe(pe)
        s_pb = _score_pb(pb)
        s_chg = _score_change_pct(chg)
        basic_score = s_pe * 0.35 + s_pb * 0.30 + s_chg * 0.35

        # 综合
        total = tech_score * w_tech + fund_score * w_fund + basic_score * w_basic

        results.append({
            "row": row,
            "tech": round(tech_score, 1),
            "fund": round(fund_score, 1),
            "basic": round(basic_score, 1),
            "total": round(total, 1),
            "details": {
                "rsi_score": round(s_rsi, 1),
                "ma_score": round(s_ma, 1),
                "volume_ratio_score": round(s_vr, 1),
                "main_flow_score": round(fund_score, 1),
                "pe_score": round(s_pe, 1),
                "pb_score": round(s_pb, 1),
                "change_score": round(s_chg, 1),
            },
        })
    return results


def score_to_label(total):
    """评分转建议标签。"""
    if total >= 80:
        return "强烈关注"
    elif total >= 65:
        return "关注"
    elif total >= 50:
        return "观望"
    elif total >= 35:
        return "谨慎"
    else:
        return "回避"


def cmd_rank(rows, col_map, headers, args):
    """综合评分排序。"""
    w_tech = getattr(args, "weight_tech", 0.4)
    w_fund = getattr(args, "weight_fund", 0.3)
    w_basic = getattr(args, "weight_basic", 0.3)

    scores = compute_scores(rows, col_map, w_tech, w_fund, w_basic)
    scores.sort(key=lambda x: x["total"], reverse=True)

    name_col = col_map.get("name", "")
    code_col = col_map.get("code", "")

    print(f"{'排名':<4} {'代码':<10} {'名称':<12} {'综合':<6} {'技术':<6} {'资金':<6} {'基本面':<6} {'建议':<8}")
    print("-" * 68)
    for i, s in enumerate(scores, 1):
        row = s["row"]
        code = row.get(code_col, "") if code_col else ""
        name = row.get(name_col, "") if name_col else ""
        label = score_to_label(s["total"])
        print(f"{i:<4} {code:<10} {name:<12} {s['total']:<6} {s['tech']:<6} {s['fund']:<6} {s['basic']:<6} {label:<8}")

    if args.output:
        out_rows = []
        for s in scores:
            r = dict(s["row"])
            r["_score_total"] = s["total"]
            r["_score_tech"] = s["tech"]
            r["_score_fund"] = s["fund"]
            r["_score_basic"] = s["basic"]
            r["_suggestion"] = score_to_label(s["total"])
            out_rows.append(r)

        out_cols = list(scores[0]["row"].keys()) + ["_score_total", "_score_tech", "_score_fund", "_score_basic", "_suggestion"]
        try:
            with open(args.output, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=out_cols)
                writer.writeheader()
                writer.writerows(out_rows)
            print(f"\n排名结果已保存: {args.output}")
        except Exception as e:
            print(f"错误: 保存文件失败: {e}", file=sys.stderr)


def cmd_score(rows, col_map, headers, args):
    """单只股票详细评分。"""
    code_col = col_map.get("code", "")
    name_col = col_map.get("name", "")
    price_col = col_map.get("price", "")

    target_code = args.code.strip()
    matched = []
    for row in rows:
        val = str(row.get(code_col, "")).strip() if code_col else ""
        if val == target_code:
            matched.append(row)
        # 也匹配名称
        nv = str(row.get(name_col, "")).strip() if name_col else ""
        if nv == target_code:
            if row not in matched:
                matched.append(row)

    if not matched:
        print(f"未找到匹配的股票: {target_code}")
        return

    r = matched[0]
    scores = compute_scores([r], col_map)
    s = scores[0]

    code = r.get(code_col, "") if code_col else target_code
    name = r.get(name_col, "") if name_col else ""
    price = r.get(price_col, "") if price_col else ""

    print("=" * 60)
    print(f"  {name} ({code})")
    if price:
        print(f"  现价: {price}")
    print("=" * 60)

    print(f"\n  📊 综合评分: {s['total']} 分  —  {score_to_label(s['total'])}")
    print(f"  ├─ 技术面: {s['tech']} 分 (权重: 40%)")
    print(f"  │   ├─ RSI评分:       {s['details']['rsi_score']}")
    print(f"  │   ├─ 均线信号评分:   {s['details']['ma_score']}")
    print(f"  │   └─ 量比评分:     {s['details']['volume_ratio_score']}")
    print(f"  ├─ 资金面: {s['fund']} 分 (权重: 30%)")
    print(f"  │   └─ 主力资金评分: {s['details']['main_flow_score']}")
    print(f"  └─ 基本面: {s['basic']} 分 (权重: 30%)")
    print(f"      ├─ PE评分:       {s['details']['pe_score']}")
    print(f"      ├─ PB评分:       {s['details']['pb_score']}")
    print(f"      └─ 涨跌幅评分:   {s['details']['change_score']}")

    # 显示原始值
    print(f"\n  原始数据:")
    if col_map.get("rsi"):
        print(f"    RSI: {r.get(col_map['rsi'], '-')}")
    if col_map.get("ma_signal"):
        print(f"    均线信号: {r.get(col_map['ma_signal'], '-')}")
    if col_map.get("volume_ratio"):
        print(f"    量比: {r.get(col_map['volume_ratio'], '-')}")
    if col_map.get("main_flow"):
        print(f"    主力净流入: {r.get(col_map['main_flow'], '-')}")
    if col_map.get("pe"):
        print(f"    PE: {r.get(col_map['pe'], '-')}")
    if col_map.get("pb"):
        print(f"    PB: {r.get(col_map['pb'], '-')}")

    print(DISCLAIMER)


def cmd_summary(rows, col_map, headers, args):
    """筛选摘要统计。"""
    print("=" * 60)
    print("  股票池概览")
    print("=" * 60)
    print(f"  总股票数: {len(rows)}")

    # 统计各列分布
    stat_fields = [
        ("rsi", "RSI", [("<30", lambda v: v is not None and v < 30),
                         ("30-50", lambda v: v is not None and 30 <= v <= 50),
                         ("50-70", lambda v: v is not None and 50 < v <= 70),
                         (">70", lambda v: v is not None and v > 70)]),
        ("volume_ratio", "量比", [("<0.5", lambda v: v is not None and v < 0.5),
                                    ("0.5-1.0", lambda v: v is not None and 0.5 <= v <= 1.0),
                                    ("1.0-1.5", lambda v: v is not None and 1.0 < v <= 1.5),
                                    (">1.5", lambda v: v is not None and v > 1.5)]),
        ("change_pct", "涨跌幅", [("<-3%", lambda v: v is not None and v < -3),
                                     ("-3~0%", lambda v: v is not None and -3 <= v < 0),
                                     ("0~3%", lambda v: v is not None and 0 <= v <= 3),
                                     (">3%", lambda v: v is not None and v > 3)]),
    ]

    for std_key, display, buckets in stat_fields:
        col = col_map.get(std_key)
        if not col:
            continue
        vals = [safe_float(r.get(col, "")) for r in rows]
        if not vals:
            continue
        print(f"\n  {display} 分布:")
        for label, test in buckets:
            cnt = sum(1 for v in vals if test(v))
            pct = cnt / len(rows) * 100 if rows else 0
            bar = "█" * int(pct // 2.5) if pct > 0 else ""
            print(f"    {label:<10} {cnt:>4} ({pct:5.1f}%) {bar}")

    # 均值统计
    print(f"\n  均值统计:")
    avg_fields = [
        ("rsi", "RSI"),
        ("volume_ratio", "量比"),
        ("pe", "PE"),
        ("pb", "PB"),
        ("change_pct", "涨跌幅(%)"),
        ("main_flow", "主力净流入"),
    ]
    for std_key, display in avg_fields:
        col = col_map.get(std_key)
        if not col:
            continue
        vals = [safe_float(r.get(col, "")) for r in rows if safe_float(r.get(col, "")) is not None]
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        low = min(vals)
        high = max(vals)
        print(f"    {display:<10} 均值={avg:.2f}  范围=[{low:.2f}, {high:.2f}]")

    # 综合评分排名前/后5
    scores = compute_scores(rows, col_map)
    scores.sort(key=lambda x: x["total"], reverse=True)
    name_col = col_map.get("name", "")
    code_col = col_map.get("code", "")

    print(f"\n  TOP 5:")
    for i, s in enumerate(scores[:5], 1):
        code = s["row"].get(code_col, "") if code_col else ""
        name = s["row"].get(name_col, "") if name_col else ""
        print(f"    {i}. {name} ({code}) — {s['total']}分 — {score_to_label(s['total'])}")

    print(f"\n  BOTTOM 5:")
    for i, s in enumerate(scores[-5:][::-1], 1):
        code = s["row"].get(code_col, "") if code_col else ""
        name = s["row"].get(name_col, "") if name_col else ""
        print(f"    {i}. {name} ({code}) — {s['total']}分 — {score_to_label(s['total'])}")

    print(DISCLAIMER)


def cmd_correlation(rows, col_map, headers, args):
    """因子相关性分析。"""
    numeric_keys = ["rsi", "volume_ratio", "main_flow", "pe", "pb", "market_cap", "change_pct"]
    available = [(k, col_map[k]) for k in numeric_keys if k in col_map]

    if len(available) < 2:
        print("错误: 需要至少2个数值列来计算相关性", file=sys.stderr)
        return

    # 提取数据
    data = {}
    for std_key, col in available:
        vals = []
        for row in rows:
            v = safe_float(row.get(col, ""))
            if v is not None:
                vals.append(v)
        if len(vals) >= 5:
            data[std_key] = vals

    keys = list(data.keys())
    if len(keys) < 2:
        print("错误: 有效数据不足 (每个列至少需要5个有效值)", file=sys.stderr)
        return

    # 计算相关系数矩阵
    def pearson(x, y):
        n = min(len(x), len(y))
        if n < 3:
            return 0.0
        mx, my = sum(x[:n]) / n, sum(y[:n]) / n
        num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
        dx = sum((x[i] - mx) ** 2 for i in range(n))
        dy = sum((y[i] - my) ** 2 for i in range(n))
        if dx == 0 or dy == 0:
            return 0.0
        return num / (math.sqrt(dx) * math.sqrt(dy))

    labels = {
        "rsi": "RSI", "volume_ratio": "量比", "main_flow": "主力资金",
        "pe": "PE", "pb": "PB", "market_cap": "市值", "change_pct": "涨跌幅",
    }

    print(f"\n  因子相关性矩阵 (Pearson r)\n")
    # 表头
    header = f"{'':<12}"
    for k in keys:
        header += f"{labels.get(k, k):<10}"
    print(header)
    print("-" * (12 + 10 * len(keys)))

    for k1 in keys:
        row_line = f"{labels.get(k1, k1):<12}"
        for k2 in keys:
            if k1 == k2:
                row_line += f"{'1.00':<10}"
            else:
                r = pearson(data[k1], data[k2])
                color = " " if abs(r) < 0.3 else "!" if abs(r) < 0.7 else "*"
                row_line += f"{r:>+6.2f}{color:<3}"
        print(row_line)

    print("\n  注: * 强相关(|r|≥0.7)  ! 中等相关(0.3≤|r|<0.7)")

    # 解读
    print(f"\n  解读:")
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            r = pearson(data[keys[i]], data[keys[j]])
            if abs(r) >= 0.7:
                direction = "正相关" if r > 0 else "负相关"
                print(f"    {labels.get(keys[i], keys[i])} 与 {labels.get(keys[j], keys[j])}: "
                      f"强{direction} (r={r:+.3f})")
            elif abs(r) >= 0.3:
                direction = "正相关" if r > 0 else "负相关"
                print(f"    {labels.get(keys[i], keys[i])} 与 {labels.get(keys[j], keys[j])}: "
                      f"中等{direction} (r={r:+.3f})")


# ─── CLI ─────────────────────────────────────────────────

def build_parser():
    # 共享父参数：--file/--output 在顶层与每个子命令后都可用（文档写法为 `rank --file x.csv`）
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--file", required=False, help="股票数据CSV文件路径")
    parent.add_argument("--output", help="输出文件路径 (filter/rank命令)")

    parser = argparse.ArgumentParser(
        description="Stock Screener — 多因子选股器 v1.0.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parent],
        epilog=(
            "示例:\n"
            "  python3 scripts/screener.py filter --file stocks.csv --rsi-min 30 --rsi-max 70\n"
            "  python3 scripts/screener.py filter --file stocks.csv --volume-ratio-min 1.5 --fundflow-min 0\n"
            "  python3 scripts/screener.py rank --file stocks.csv --output ranked.csv\n"
            "  python3 scripts/screener.py score --file stocks.csv --code 600519\n"
            "  python3 scripts/screener.py summary --file stocks.csv\n"
            "  python3 scripts/screener.py correlation --file stocks.csv\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令", parser_class=argparse.ArgumentParser)

    # filter
    p_filter = subparsers.add_parser("filter", parents=[parent], help="多条件筛选股票")
    p_filter.add_argument("--rsi-min", type=float, help="RSI最小值")
    p_filter.add_argument("--rsi-max", type=float, help="RSI最大值")
    p_filter.add_argument("--ma-signal", help="均线信号 (bullish/bearish/cross)")
    p_filter.add_argument("--volume-ratio-min", type=float, help="最小量比")
    p_filter.add_argument("--fundflow-min", type=float, help="最小主力净流入")
    p_filter.add_argument("--pe-min", type=float, help="PE最小值")
    p_filter.add_argument("--pe-max", type=float, help="PE最大值")
    p_filter.add_argument("--pb-min", type=float, help="PB最小值")
    p_filter.add_argument("--pb-max", type=float, help="PB最大值")
    p_filter.add_argument("--price-min", type=float, help="价格最小值")
    p_filter.add_argument("--price-max", type=float, help="价格最大值")
    p_filter.add_argument("--market-cap-min", type=float, help="市值最小值")
    p_filter.add_argument("--market-cap-max", type=float, help="市值最大值")
    p_filter.add_argument("--change-min", type=float, help="涨跌幅最小值")
    p_filter.add_argument("--change-max", type=float, help="涨跌幅最大值")

    # rank
    p_rank = subparsers.add_parser("rank", parents=[parent], help="综合评分排序")
    p_rank.add_argument("--weight-tech", type=float, default=0.4, help="技术面权重 (默认0.4)")
    p_rank.add_argument("--weight-fund", type=float, default=0.3, help="资金面权重 (默认0.3)")
    p_rank.add_argument("--weight-basic", type=float, default=0.3, help="基本面权重 (默认0.3)")

    # score
    p_score = subparsers.add_parser("score", parents=[parent], help="单只股票详细评分")
    p_score.add_argument("--code", required=True, help="股票代码或名称")

    # summary
    subparsers.add_parser("summary", parents=[parent], help="数据摘要统计")

    # correlation
    subparsers.add_parser("correlation", parents=[parent], help="因子相关性分析")

    return parser


def main():
    parser = build_parser()
    # 支持从 sys.argv 提取 --file 和 --output 到顶层
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print(DISCLAIMER)
        return

    if not getattr(args, "file", None):
        print("错误: 必须提供 --file <csv>", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    rows, col_map, headers = load_csv(args.file)

    # 列映射诊断
    found = [k for k in col_map]
    if not found:
        print("警告: 未识别到任何标准列名。请检查CSV表头。", file=sys.stderr)
        print(f"当前表头: {headers}", file=sys.stderr)
        sys.exit(1)

    commands = {
        "filter": cmd_filter,
        "rank": cmd_rank,
        "score": cmd_score,
        "summary": cmd_summary,
        "correlation": cmd_correlation,
    }

    commands[args.command](rows, col_map, headers, args)
    print(DISCLAIMER)


if __name__ == "__main__":
    main()
