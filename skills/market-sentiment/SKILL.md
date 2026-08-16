---
name: market-sentiment
model: default
description: |
  四维度市场情绪评估（情绪/趋势/量能/宽度极端度），对大盘环境诊断并输出 0–100 评分与对应市场状态。
  Use when: 用户请求市场情绪分析、大盘诊断、超买超卖判断、涨跌比/涨停跌停比分析。
  触发词：market sentiment, 市场情绪, 大盘分析, 超买, 超卖, 情绪评分, trend
disclosure:
  cloud: false
  network: []
  offline_mode: true
  api_keys: []
  jurisdiction: []
  retention: "none"
permissions:
  network: []
  filesystem:
    write: []
  env: []

---

> ⚠️ **免责声明**：本工具为辅助性参考工具，**不构成投资建议，不构成法律建议**。市场有风险，投资需谨慎；据此操作，风险自担。正式合规意见请咨询具备资质的律师。最终决策与责任由使用者自行承担。

# 📊 Market Sentiment — 市场情绪分析器

基于**四维度市场情绪评估模型**，对大盘环境进行诊断分析，输出 0–100 综合评分及对应的市场状态。

## 核心功能

- **analyze** — 综合情绪分析（含评分、状态、操作建议）
- **score** — 评分明细（四维度 + ASCII 条形图）
- **trend** — 多日趋势追踪
- **summary** — 一句话市场诊断

## 四维度模型

| 维度 | 满分 | 权重 | 说明 |
|------|------|------|
| 情绪极端度 | 30 | 30% | 涨停/跌停比、涨跌比、连板效应 |
| 趋势极端度 | 30 | 30% | 指数涨跌幅、MA20 偏离、平均涨跌 |
| 量能极端度 | 20 | 20% | 量比、成交额变化 |
| 宽度极端度 | 20 | 20% | MA20 占比、新高/新低比、大小盘分化 |

## 状态映射

| 评分 | 状态 | planner 参数 |
|------|------|-------------|
| ≥ 75 | 超买 (overbought) | bear |
| 65–74 | 偏强 (strong) | strong |
| 45–64 | 中性 (neutral) | oscillate |
| 30–44 | 偏弱 (weak) | weak |
| < 30 | 超卖 (oversold) | moderate |

## 集成工作流

本工具是股票分析工具链中的一环，完整链路如下：

```
fund-flow (资金面) ──┐
                     ├──→ stock-screener (多因子选股) ──→ stock-planner (交易计划)
market-signals (技术面) ──┘
market-sentiment (情绪面) ──→ 提供 market 参数给 stock-planner
```

```bash
# 1. 分析市场情绪
python3 scripts/sentiment.py analyze --file market_data.csv

# 2. 获取市场参数，传给 stock-planner
python3 scripts/stock_planner.py --plan \
  --market $(python3 scripts/sentiment.py summary --file market_data.csv | grep 'planner' | awk '{print $NF}')
```

## 触发关键词

市场情绪、大盘环境、sentiment、market context、情绪分析、大盘诊断、market state、overbought、oversold、市场状态

## 法律免责声明

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
