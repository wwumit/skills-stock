# 📊 Market Sentiment — 市场情绪分析器

基于**四维度市场情绪评估模型**的大盘环境诊断工具。分析全市场情绪指标并输出市场状态，可与 stock-planner 集成。

## 快速开始

```bash
# 分析市场情绪
python3 scripts/sentiment.py analyze --file market_data.csv

# 评分明细
python3 scripts/sentiment.py score --file market_data.csv

# 多日趋势
python3 scripts/sentiment.py trend --file market_data.csv

# 一句话摘要
python3 scripts/sentiment.py summary --file market_data.csv
```

## 输入格式

支持包含以下字段的 CSV 文件（列名自动识别中英文）：

| 数据 | 可识别的列名 |
|------|-------------|
| 日期 | date, 日期, trade_date |
| 指数涨跌幅 | change_pct, change, 涨跌幅 |
| 涨停家数 | close_limit_up, limit_up, 涨停 |
| 跌停家数 | close_limit_down, limit_down, 跌停 |
| 上涨家数 | advance_count, advance, 上涨 |
| 下跌家数 | decline_count, decline, 下跌 |
| 成交额 | amount, turnover, 成交额 |
| 成交量 | volume, vol, 成交量 |
| 高于MA20 | above_ma20, above_ma20_pct, 高于MA20 |
| 52周新高 | new_high, new_52w_high, 新高 |
| 52周新低 | new_low, new_52w_low, 新低 |
| 平均涨跌 | avg_change, avg_pct, 平均涨跌 |

## 输出

```json
{
  "date": "2026-07-19",
  "total_score": 42,
  "level": "weak",
  "signal": "市场情绪偏弱，建议控制仓位",
  "dimensions": {
    "emotion": {"score": 12, "max": 30, "detail": "涨停占比35%, 涨跌比38%"},
    "trend":  {"score": 15, "max": 30, "detail": "沪深300 -1.2%, 偏离均线-3.5%"},
    "volume": {"score": 8,  "max": 20, "detail": "量比0.7, 缩量"},
    "breadth": {"score": 7,  "max": 20, "detail": "高于MA20占比28%, 新高/新低=0.3"}
  },
  "market_state": "weak",
  "planner_param": "weak",
  "suggested_position": "减仓至5只，止损收紧至6%",
  "suggested_threshold": 7.0
}
```

## 效果案例

### 案例：弱势市场（评分 42）

输入数据特征：
- 沪深300 跌 -1.2%，涨停/跌停比 35%/65%
- 上涨/下跌家数比 38%/62%
- 成交额缩量至近5日均值的 70%
- 高于MA20 个股仅占 28%，新高/新低比 0.3

输出结果：
```
═══════════════════════════════════════════════
  市场情绪分析报告
═══════════════════════════════════════════════
  日期:         2026-07-19
  综合评分:     42.0/100
  市场状态:     偏弱 (weak)
  stock-planner: --market weak
  信号:         市场情绪偏弱，建议控制仓位，注意风险
  建议仓位:     减仓至4-5只，止损收紧至6%
  建议阈值:     7.0%
  ── 四维度评分 ──
  ① 情绪极端度: 12.0/30 — 涨停占比35%, 涨跌比38%, 情绪偏弱
  ② 趋势极端度: 15.0/30 — 沪深300 -1.2%, 高于MA20占比28%, 趋势偏弱
  ③ 量能极端度: 8.0/20 — 量比0.7, 缩量
  ④ 宽度极端度: 7.0/20 — 高于MA20占比28%, 新高/新低=0.3, 宽度较差
═══════════════════════════════════════════════
```

### 案例：强势市场（评分 78）

输入数据特征：
- 沪深300 涨 +2.1%，涨停/跌停比 82%/18%
- 上涨/下跌家数比 75%/25%
- 成交额放量至近5日均值的 150%
- 高于MA20 个股占 82%，新高/新低比 0.85

输出结果：
```
═══════════════════════════════════════════════
  市场情绪分析报告
═══════════════════════════════════════════════
  日期:         2026-07-15
  综合评分:     78.0/100
  市场状态:     超买 (overbought)
  stock-planner: --market bear
  信号:         市场情绪过热，短期回调风险加大，建议谨慎追高
  建议仓位:     减仓至4只以内，不开新仓，逢高减磅
  建议阈值:     6.5%
  ── 四维度评分 ──
  ① 情绪极端度: 26.0/30 — 涨停占比82%, 涨跌比75%, 情绪极强
  ② 趋势极端度: 25.0/30 — 沪深300 +2.1%, 高于MA20占比82%, 趋势极强
  ③ 量能极端度: 18.0/20 — 量比1.5, 放量
  ④ 宽度极端度: 9.0/20 — 高于MA20占比82%, 新高/新低=0.85, 宽度极好
═══════════════════════════════════════════════
```

## 与 stock-planner 集成

```bash
# 分析市场情绪后，将 market 参数传给 planner
python3 scripts/stock_planner.py --plan --market \
  $(python3 scripts/sentiment.py summary --file market_data.csv | grep 'planner' | awk '{print $NF}')
```

## 依赖

- Python 3.8+
- 纯标准库，无外部依赖

## 法律声明

**重要声明：**
1. **非投资建议**：本工具输出的所有评分、状态、操作建议仅供参考，不构成任何形式的投资建议、买卖推荐或业绩承诺。
2. **数据准确性**：本工具的分析结果依赖于输入数据的准确性和完整性。作者不对数据源错误、缺失或延迟导致的任何损失承担责任。
3. **用户决策**：所有投资决策应由用户独立做出。用户应结合自身风险承受能力、财务状况和专业意见进行判断。
4. **过往表现**：历史数据的分析结果不代表未来市场表现。市场存在不可预测的风险因素。
5. **责任限制**：在法律允许的最大范围内，作者和贡献者不对因使用本工具产生的任何直接或间接损失承担责任。

**Disclaimer (English):**
1. **Not Investment Advice**: All scores, statuses, and suggestions are for reference only and do not constitute investment advice.
2. **Data Accuracy**: Analysis depends on input data quality. The author is not liable for data source errors.
3. **User Decision**: All investment decisions should be made independently by the user.
4. **Past Performance**: Historical analysis does not guarantee future results.
5. **Limitation of Liability**: To the maximum extent permitted by law, the author and contributors shall not be liable for any losses arising from the use of this tool.
