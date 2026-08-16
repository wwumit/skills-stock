#!/usr/bin/env python3
"""
Market Sentiment Analyzer — 市场情绪分析器
============================================

基于四维度市场情绪评估模型，对大盘环境进行诊断分析。
输出0-100综合评分及对应的市场状态，可与 stock-planner 集成。

用法:
    python3 sentiment.py analyze --file market_data.csv
    python3 sentiment.py analyze --file market_data.csv --output sentiment.json
    python3 sentiment.py score --file market_data.csv
    python3 sentiment.py trend --file market_data.csv
    python3 sentiment.py summary --file market_data.csv

免责声明:
    本工具仅供辅助参考，不构成任何投资建议。市场有风险，投资需谨慎。
    作者和贡献者不对因使用本工具产生的任何损失承担责任。
"""

import argparse
import csv
import json
import math
import os
import sys
from collections import OrderedDict

# ──────────────────────────────────────────────
# 列名映射（灵活识别中英文）
# ──────────────────────────────────────────────
COLUMN_MAP = {
    'date': ['date', '日期', 'trade_date', 'trade_date'],
    'index_name': ['index', '指数', 'name', 'index_name', '品种'],
    'change_pct': ['change_pct', 'change', 'pct_chg', '涨跌幅', '涨幅', '涨跌幅%', 'change_percent'],
    'close_limit_up': ['close_limit_up', 'limit_up', '涨停', '涨停家数', 'close_limit_up_cnt'],
    'close_limit_down': ['close_limit_down', 'limit_down', '跌停', '跌停家数', 'close_limit_down_cnt'],
    'advance_count': ['advance_count', 'advance', '上涨', '涨', 'advance_cnt', 'raise'],
    'decline_count': ['decline_count', 'decline', '下跌', '跌', 'decline_cnt', 'fall'],
    'volume': ['volume', 'vol', '成交量', 'volume_total', 'vol_total', '成交量(亿)'],
    'amount': ['amount', 'turnover', '成交额', '成交额(亿)', 'amount_total', 'amt'],
    'new_high': ['new_high', 'new_52w_high', '新高', '52周新高', 'new_high_52w'],
    'new_low': ['new_low', 'new_52w_low', '新低', '52周新低', 'new_low_52w'],
    'above_ma20': ['above_ma20', 'above_ma20_pct', '高于MA20', 'above_ma20%%', 'above_ma20_pct'],
    'avg_change': ['avg_change', 'avg_pct', '平均涨跌', 'avg_change_pct', '平均涨跌幅'],
    'close': ['close', '收盘', 'close_price', '收盘价'],
    'count': ['count', 'total', '总数', 'total_count', '样本数'],
}


def _find_column(row, candidates):
    """查找第一个匹配的列名"""
    for c in candidates:
        if c in row:
            return c
    return None


def _safe_float(val, default=0.0):
    """安全转浮点"""
    if val is None or val == '':
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=0):
    """安全转整数"""
    if val is None or val == '':
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


# ──────────────────────────────────────────────
# CSV 读取
# ──────────────────────────────────────────────

def read_market_csv(filepath):
    """读取市场数据CSV，返回行列表（每行为OrderedDict）"""
    rows = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(OrderedDict(row))
    if not rows:
        raise ValueError("CSV 文件为空")
    return rows, list(rows[0].keys())


# ──────────────────────────────────────────────
# 四个维度评分
# ──────────────────────────────────────────────

def score_emotion(row, col_index):
    """维度1：情绪极端度（满分30分）"""
    score = 0
    max_score = 30
    details = []

    # 涨停/跌停比（15分）
    limit_up_col = _find_column(col_index, COLUMN_MAP['close_limit_up'])
    limit_down_col = _find_column(col_index, COLUMN_MAP['close_limit_down'])
    if limit_up_col and limit_down_col:
        up_cnt = _safe_int(row.get(limit_up_col))
        down_cnt = _safe_int(row.get(limit_down_col))
        total_limit = up_cnt + down_cnt
        if total_limit > 0:
            ratio = up_cnt / total_limit
            if ratio > 0.8:
                score += 12 + min(3, (ratio - 0.8) * 30)
                details.append(f"涨停占比{ratio:.0%}, 情绪极强")
            elif ratio > 0.6:
                score += 9 + (ratio - 0.6) * 30
                details.append(f"涨停占比{ratio:.0%}, 偏强")
            elif ratio > 0.4:
                score += 6 + (ratio - 0.4) * 30
                details.append(f"涨停占比{ratio:.0%}, 中性")
            elif ratio > 0.2:
                score += 3 + (ratio - 0.2) * 30
                details.append(f"涨停占比{ratio:.0%}, 偏弱")
            else:
                score += 0 + ratio * 15
                details.append(f"涨停占比{ratio:.0%}, 极弱")
        else:
            details.append("涨停/跌停均为0，无情绪信号")
    else:
        details.append("缺少涨停/跌停数据")

    # 涨跌比（10分）
    adv_col = _find_column(col_index, COLUMN_MAP['advance_count'])
    dec_col = _find_column(col_index, COLUMN_MAP['decline_count'])
    if adv_col and dec_col:
        adv = _safe_int(row.get(adv_col))
        dec = _safe_int(row.get(dec_col))
        total_ad = adv + dec
        if total_ad > 0:
            adv_ratio = adv / total_ad
            if adv_ratio > 0.7:
                score += 9 + min(1, (adv_ratio - 0.7) * 10)
                details.append(f"涨跌比{adv_ratio:.0%}, 普涨")
            elif adv_ratio > 0.55:
                score += 6 + (adv_ratio - 0.55) * 20
                details.append(f"涨跌比{adv_ratio:.0%}, 偏涨")
            elif adv_ratio > 0.45:
                score += 4 + (adv_ratio - 0.45) * 20
                details.append(f"涨跌比{adv_ratio:.0%}, 平衡")
            elif adv_ratio > 0.3:
                score += 2 + (adv_ratio - 0.3) * 13
                details.append(f"涨跌比{adv_ratio:.0%}, 偏跌")
            else:
                score += adv_ratio * 6.7
                details.append(f"涨跌比{adv_ratio:.0%}, 普跌")
        else:
            details.append("涨跌总数均为0")
    else:
        details.append("缺少涨跌家数数据")

    # 连板效应（5分）— 使用涨停占比推断
    if limit_up_col and limit_down_col and total_limit > 0:
        batch_score = min(5, total_limit / 50 * 5)
        score += batch_score

    score = min(score, max_score)
    return score, max_score, "; ".join(details)


def score_trend(row, col_index, prev_rows=None):
    """维度2：趋势极端度（满分30分）"""
    score = 0
    max_score = 30
    details = []

    # 涨跌幅（15分）
    chg_col = _find_column(col_index, COLUMN_MAP['change_pct'])
    if chg_col:
        chg = _safe_float(row.get(chg_col))
        if chg > 3.5:
            score += 14 + min(1, (chg - 3.5) / 2)
            details.append(f"涨幅{chg:.1f}%, 强势")
        elif chg > 2.0:
            score += 11 + (chg - 2.0) * 2
            details.append(f"涨幅{chg:.1f}%, 偏强")
        elif chg > 0.5:
            score += 7 + (chg - 0.5) * 2.7
            details.append(f"涨幅{chg:.1f}%, 微涨")
        elif chg > -0.5:
            score += 5 + chg * 4
            details.append(f"涨幅{chg:.1f}%, 窄幅震荡")
        elif chg > -2.0:
            score += 4 + (chg + 0.5) * 2
            details.append(f"涨幅{chg:.1f}%, 偏弱")
        elif chg > -3.5:
            score += 2 + (chg + 2.0) * 1.3
            details.append(f"涨幅{chg:.1f}%, 弱势")
        else:
            score += max(0, 0 + (chg + 3.5) / 3.5 * 2)
            details.append(f"涨幅{chg:.1f}%, 恐慌")
    else:
        details.append("缺少涨跌幅数据")

    # 与MA20偏离（8分）
    above_col = _find_column(col_index, COLUMN_MAP['above_ma20'])
    if above_col:
        above_pct = _safe_float(row.get(above_col))
        if above_pct > 0.7:
            score += 8
            details.append(f"高于MA20占比{above_pct:.0%}, 趋势极强")
        elif above_pct > 0.55:
            score += 6 + (above_pct - 0.55) * 13
            details.append(f"高于MA20占比{above_pct:.0%}, 趋势偏强")
        elif above_pct > 0.45:
            score += 4 + (above_pct - 0.45) * 20
            details.append(f"高于MA20占比{above_pct:.0%}, 均衡")
        elif above_pct > 0.3:
            score += 2 + (above_pct - 0.3) * 13
            details.append(f"高于MA20占比{above_pct:.0%}, 趋势偏弱")
        else:
            score += max(0, above_pct / 0.3 * 2)
            details.append(f"高于MA20占比{above_pct:.0%}, 趋势极弱")
    else:
        details.append("缺少MA20数据")

    # 平均涨跌幅（7分）
    avg_col = _find_column(col_index, COLUMN_MAP['avg_change'])
    if avg_col:
        avg = _safe_float(row.get(avg_col))
        if avg > 1.5:
            score += 7
            details.append(f"平均涨跌{avg:.2f}%, 个股普涨")
        elif avg > 0.5:
            score += 4 + (avg - 0.5) * 3
            details.append(f"平均涨跌{avg:.2f}%, 个股偏涨")
        elif avg > -0.5:
            score += 2 + (avg + 0.5) * 2
            details.append(f"平均涨跌{avg:.2f}%, 个股震荡")
        elif avg > -1.5:
            score += 1 + (avg + 0.5) * 1
            details.append(f"平均涨跌{avg:.2f}%, 个股偏跌")
        else:
            score += max(0, 0 + (avg + 1.5) / 1.5 * 1)
            details.append(f"平均涨跌{avg:.2f}%, 个股普跌")
    else:
        details.append("缺少平均涨跌幅数据")

    score = min(score, max_score)
    return score, max_score, "; ".join(details)


def score_volume(row, col_index, prev_rows=None):
    """维度3：量能极端度（满分20分）"""
    score = 0
    max_score = 20
    details = []

    # 成交量/成交额（20分）
    vol_col = _find_column(col_index, COLUMN_MAP['volume'])
    amt_col = _find_column(col_index, COLUMN_MAP['amount'])

    if amt_col:
        amount = _safe_float(row.get(amt_col))
        # 估算量比 (相对历史均值)
        vol_ratio_hint = 1.0
        if prev_rows and len(prev_rows) >= 5:
            amounts = []
            for pr in prev_rows:
                a = _safe_float(pr.get(amt_col, 0))
                if a > 0:
                    amounts.append(a)
            if amounts:
                avg5 = sum(amounts[-5:]) / len(amounts)
                if avg5 > 0:
                    vol_ratio_hint = amount / avg5

        if vol_ratio_hint > 1.8:
            score += 18 + min(2, (vol_ratio_hint - 1.8) * 5)
            details.append(f"量比{vol_ratio_hint:.1f}, 放量极强")
        elif vol_ratio_hint > 1.3:
            score += 14 + (vol_ratio_hint - 1.3) * 13
            details.append(f"量比{vol_ratio_hint:.1f}, 放量")
        elif vol_ratio_hint > 0.8:
            score += 10 + (vol_ratio_hint - 0.8) * 13
            details.append(f"量比{vol_ratio_hint:.1f}, 正常")
        elif vol_ratio_hint > 0.5:
            score += 5 + (vol_ratio_hint - 0.5) * 17
            details.append(f"量比{vol_ratio_hint:.1f}, 缩量")
        else:
            score += vol_ratio_hint / 0.5 * 5
            details.append(f"量比{vol_ratio_hint:.1f}, 极度缩量")
    elif vol_col:
        vol = _safe_float(row.get(vol_col))
        # 没有历史数据时做简单判断
        _ = vol  # placeholder, already scored by trend
        details.append("有成交量数据但无法计算量比（需多日数据）")
        score += 10  # 中性
    else:
        details.append("缺少成交量/额数据")
        score += 10

    score = min(score, max_score)
    return score, max_score, "; ".join(details)


def score_breadth(row, col_index, prev_rows=None):
    """维度4：宽度极端度（满分20分）"""
    score = 0
    max_score = 20
    details = []

    # 高于MA20（10分）
    above_col = _find_column(col_index, COLUMN_MAP['above_ma20'])
    if above_col:
        above_pct = _safe_float(row.get(above_col))
        if above_pct > 0.8:
            score += 10
            details.append(f"高于MA20:{above_pct:.0%}, 宽度极好")
        elif above_pct > 0.6:
            score += 7 + (above_pct - 0.6) * 15
            details.append(f"高于MA20:{above_pct:.0%}, 宽度良好")
        elif above_pct > 0.4:
            score += 5 + (above_pct - 0.4) * 10
            details.append(f"高于MA20:{above_pct:.0%}, 宽度中性")
        elif above_pct > 0.2:
            score += 3 + (above_pct - 0.2) * 10
            details.append(f"高于MA20:{above_pct:.0%}, 宽度较差")
        else:
            score += above_pct / 0.2 * 3
            details.append(f"高于MA20:{above_pct:.0%}, 宽度极差")
    else:
        details.append("缺少MA20宽度数据(上面已评分, 这里不再重复计分)")

    # 新高/新低比（7分）
    nh_col = _find_column(col_index, COLUMN_MAP['new_high'])
    nl_col = _find_column(col_index, COLUMN_MAP['new_low'])
    if nh_col and nl_col:
        nh = _safe_int(row.get(nh_col))
        nl = _safe_int(row.get(nl_col))
        total_nl = nh + nl
        if total_nl > 0:
            nh_ratio = nh / total_nl
            if nh_ratio > 0.8:
                score += 7
                details.append(f"新高/新低比{nh_ratio:.0%}, 强势市场")
            elif nh_ratio > 0.6:
                score += 5 + (nh_ratio - 0.6) * 10
                details.append(f"新高/新低比{nh_ratio:.0%}, 偏强")
            elif nh_ratio > 0.4:
                score += 3 + (nh_ratio - 0.4) * 10
                details.append(f"新高/新低比{nh_ratio:.0%}, 均衡")
            elif nh_ratio > 0.2:
                score += 1 + (nh_ratio - 0.2) * 10
                details.append(f"新高/新低比{nh_ratio:.0%}, 偏弱")
            else:
                score += nh_ratio * 5
                details.append(f"新高/新低比{nh_ratio:.0%}, 弱势市场")
        else:
            details.append("新高/新低均为0")
    else:
        details.append("缺少新高/新低数据")
        # 用其他宽度指标补充
        if not above_col:
            details.append("无宽度数据可用")

    # 大小盘分化（3分）— 使用平均涨跌幅+指数涨跌幅估算
    chg_col = _find_column(col_index, COLUMN_MAP['change_pct'])
    avg_col = _find_column(col_index, COLUMN_MAP['avg_change'])
    if chg_col and avg_col:
        chg = _safe_float(row.get(chg_col))
        avg = _safe_float(row.get(avg_col))
        diff = abs(chg - avg)
        if diff < 0.3:
            score += 3
            details.append(f"大小盘分化小(diff={diff:.1f}%)")
        elif diff < 0.8:
            score += 2
            details.append(f"大小盘分化中等(diff={diff:.1f}%)")
        elif diff < 1.5:
            score += 1
            details.append(f"大小盘分化较大(diff={diff:.1f}%)")
        else:
            details.append(f"大小盘分化极大(diff={diff:.1f}%)")
    else:
        details.append("无法计算大小盘分化")

    score = min(score, max_score)
    return score, max_score, "; ".join(details)


# ──────────────────────────────────────────────
# 综合评分
# ──────────────────────────────────────────────

def compute_market_state(total_score):
    """根据总分映射市场状态"""
    if total_score >= 75:
        return 'overbought', '超买', 'bear'
    elif total_score >= 65:
        return 'strong', '偏强', 'strong'
    elif total_score >= 45:
        return 'neutral', '中性', 'oscillate'
    elif total_score >= 30:
        return 'weak', '偏弱', 'weak'
    else:
        return 'oversold', '超卖', 'moderate'


def get_signal_text(state, score):
    """生成一句市场判断"""
    signals = {
        'overbought': '市场情绪过热，短期回调风险加大，建议谨慎追高',
        'strong': '市场情绪偏强，趋势向好，可维持积极仓位',
        'neutral': '市场情绪中性，无明显方向信号，可均衡配置',
        'weak': '市场情绪偏弱，建议控制仓位，注意风险',
        'oversold': '市场情绪超卖，可能存在超跌反弹机会，关注左侧信号',
    }
    return signals.get(state, '市场情绪评估中')


def get_position_suggestion(state, score):
    """生成仓位建议"""
    suggestions = {
        'overbought': '减仓至4只以内，不开新仓，逢高减磅',
        'strong': '维持6-8只，可适当加仓，止损8%',
        'neutral': '维持5-6只，均衡配置，止损7%',
        'weak': '减仓至4-5只，止损收紧至6%',
        'oversold': '维持3-5只，分批试探，止损6%',
    }
    return suggestions.get(state, '均衡配置')

def get_threshold_suggestion(state, score):
    """生成建议阈值"""
    thresholds = {
        'overbought': 6.5,
        'strong': 9.0,
        'neutral': 8.0,
        'weak': 7.0,
        'oversold': 8.0,
    }
    return thresholds.get(state, 7.5)


# ──────────────────────────────────────────────
# 核心分析函数
# ──────────────────────────────────────────────

def analyze_single(row, col_index, prev_rows=None):
    """分析单日市场情绪"""
    score_emo, max_emo, detail_emo = score_emotion(row, col_index)
    score_tre, max_tre, detail_tre = score_trend(row, col_index, prev_rows)
    score_vol, max_vol, detail_vol = score_volume(row, col_index, prev_rows)
    score_bre, max_bre, detail_bre = score_breadth(row, col_index, prev_rows)

    total = score_emo + score_tre + score_vol + score_bre
    max_total = max_emo + max_tre + max_vol + max_bre

    state_code, state_name, planner_param = compute_market_state(total)
    signal_line = get_signal_text(state_code, total)
    position = get_position_suggestion(state_code, total)
    threshold = get_threshold_suggestion(state_code, total)

    # 提取日期
    date_col = _find_column(col_index, COLUMN_MAP['date'])
    date_str = row.get(date_col, '') if date_col else ''

    result = OrderedDict([
        ('date', date_str),
        ('total_score', round(total, 1)),
        ('max_score', max_total),
        ('level', state_code),
        ('state_name', state_name),
        ('signal', signal_line),
        ('dimensions', {
            'emotion': {'score': round(score_emo, 1), 'max': max_emo, 'detail': detail_emo},
            'trend': {'score': round(score_tre, 1), 'max': max_tre, 'detail': detail_tre},
            'volume': {'score': round(score_vol, 1), 'max': max_vol, 'detail': detail_vol},
            'breadth': {'score': round(score_bre, 1), 'max': max_bre, 'detail': detail_bre},
        }),
        ('market_state', state_code),
        ('planner_param', planner_param),
        ('suggested_position', position),
        ('suggested_threshold', threshold),
    ])
    return result


# ──────────────────────────────────────────────
# 命令处理
# ──────────────────────────────────────────────

def cmd_analyze(args):
    """analyze — 市场情绪分析"""
    rows, headers = read_market_csv(args.file)

    result = analyze_single(rows[-1], headers, rows[:-1] if len(rows) > 1 else None)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✓ 结果已保存到 {args.output}")

    print("═" * 55)
    print(f"  市场情绪分析报告")
    print("═" * 55)
    print(f"  日期:         {result['date']}")
    print(f"  综合评分:     {result['total_score']}/{result['max_score']}")
    print(f"  市场状态:     {result['state_name']} ({result['level']})")
    print(f"  stock-planner: --market {result['planner_param']}")
    print(f"  信号:         {result['signal']}")
    print(f"  建议仓位:     {result['suggested_position']}")
    print(f"  建议阈值:     {result['suggested_threshold']:.1f}%")
    print()
    print("  ── 四维度评分 ──")
    print(f"  ① 情绪极端度: {result['dimensions']['emotion']['score']}/{result['dimensions']['emotion']['max']}")
    print(f"     {result['dimensions']['emotion']['detail']}")
    print(f"  ② 趋势极端度: {result['dimensions']['trend']['score']}/{result['dimensions']['trend']['max']}")
    print(f"     {result['dimensions']['trend']['detail']}")
    print(f"  ③ 量能极端度: {result['dimensions']['volume']['score']}/{result['dimensions']['volume']['max']}")
    print(f"     {result['dimensions']['volume']['detail']}")
    print(f"  ④ 宽度极端度: {result['dimensions']['breadth']['score']}/{result['dimensions']['breadth']['max']}")
    print(f"     {result['dimensions']['breadth']['detail']}")
    print("═" * 55)

    return result


def cmd_score(args):
    """score — 评分明细"""
    rows, headers = read_market_csv(args.file)
    result = analyze_single(rows[-1], headers, rows[:-1] if len(rows) > 1 else None)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✓ 结果已保存到 {args.output}")

    print("═" * 60)
    print(f"  市场情绪评分明细")
    print("═" * 60)
    print(f"  日期: {result['date']}")
    print()

    dims = [
        ('情绪极端度', 'emotion', 'emotion'),
        ('趋势极端度', 'trend', 'trend'),
        ('量能极端度', 'volume', 'volume'),
        ('宽度极端度', 'breadth', 'breadth'),
    ]
    for dname, dkey, label in dims:
        dim = result['dimensions'][dkey]
        bar_len = int(dim['score'] / dim['max'] * 20) if dim['max'] > 0 else 0
        bar = '█' * bar_len + '░' * (20 - bar_len)
        pct = dim['score'] / dim['max'] * 100 if dim['max'] > 0 else 0
        print(f"  {dname}")
        print(f"  [{bar}] {dim['score']}/{dim['max']} ({pct:.0f}%)")
        print(f"  {dim['detail']}")
        print()

    print(f"  综合评分: {result['total_score']}/{result['max_score']}")
    print(f"  市场状态: {result['state_name']} ({result['level']}) → --market {result['planner_param']}")
    print(f"  {result['signal']}")
    print("═" * 60)


def cmd_trend(args):
    """trend — 多日趋势"""
    rows, headers = read_market_csv(args.file)
    if len(rows) < 2:
        print("错误: 至少需要2行数据来分析趋势")
        sys.exit(1)

    results = []
    for i, row in enumerate(rows):
        prev = rows[:i] if i > 0 else None
        r = analyze_single(row, headers, prev)
        results.append(r)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"✓ 趋势数据已保存到 {args.output}")

    print("═" * 60)
    print(f"  市场情绪趋势分析 ({len(results)}日)")
    print("═" * 60)
    print(f"  {'日期':<14} {'评分':<6} {'状态':<10} {'方向':<6}")
    print("  " + "─" * 40)

    for i, r in enumerate(results):
        arrow = ''
        if i > 0:
            prev = results[i-1]['total_score']
            curr = r['total_score']
            diff = curr - prev
            if diff > 5:
                arrow = '↑↑'
            elif diff > 1:
                arrow = '↑'
            elif diff < -5:
                arrow = '↓↓'
            elif diff < -1:
                arrow = '↓'
            else:
                arrow = '→'
        print(f"  {r['date']:<14} {r['total_score']:<6.1f} {r['state_name']:<10} {arrow:<6}")

    print()
    first = results[0]
    last = results[-1]
    diff = last['total_score'] - first['total_score']
    if diff > 0:
        trend_word = f"上升 {diff:.1f}分"
    elif diff < 0:
        trend_word = f"下降 {abs(diff):.1f}分"
    else:
        trend_word = "持平"
    print(f"  趋势: 从 {first['total_score']} 到 {last['total_score']}, {trend_word}")
    print(f"  初始状态: {first['state_name']} → 最新状态: {last['state_name']}")
    print("═" * 60)


def cmd_summary(args):
    """summary — 一句话摘要"""
    rows, headers = read_market_csv(args.file)
    result = analyze_single(rows[-1], headers, rows[:-1] if len(rows) > 1 else None)

    print(f"📊 {result['date']} | 市场情绪 {result['state_name']} ({result['total_score']}分)")
    print(f"   {result['signal']}")
    print(f"   [操作建议] {result['suggested_position']}")

    dims_indicators = []
    for dim_key in ['emotion', 'trend', 'volume', 'breadth']:
        d = result['dimensions'][dim_key]
        dims_indicators.append(f"{d['score']}/{d['max']}")

    print(f"   四维评分: {' | '.join(dims_indicators)}")
    print(f"   与stock-planner: --market {result['planner_param']}")


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='📊 Market Sentiment Analyzer — 市场情绪分析器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python3 sentiment.py analyze --file market_data.csv
    python3 sentiment.py analyze --file market_data.csv --output sentiment.json
    python3 sentiment.py score --file market_data.csv
    python3 sentiment.py trend --file market_data.csv
    python3 sentiment.py summary --file market_data.csv

与 stock-planner 集成:
    python3 stock_planner.py --market $(python3 sentiment.py summary --file market_data.csv | grep 'market' | awk '{print $NF}')

免责声明:
    本工具仅供辅助参考，不构成任何投资建议。市场有风险，投资需谨慎。
        """
    )
    parser.add_argument('command', nargs='?', default='analyze',
                        choices=['analyze', 'score', 'trend', 'summary'],
                        help='子命令: analyze, score, trend, summary (默认分析)')
    parser.add_argument('--file', '-f', required=True,
                        help='市场数据CSV文件路径')
    parser.add_argument('--output', '-o',
                        help='输出JSON文件路径（可选）')

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"错误: 文件不存在: {args.file}")
        sys.exit(1)

    commands = {
        'analyze': cmd_analyze,
        'score': cmd_score,
        'trend': cmd_trend,
        'summary': cmd_summary,
    }
    commands[args.command](args)


if __name__ == '__main__':
    main()
