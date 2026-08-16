# 🔎 Stock Screener — 多因子选股器

## Overview

连接 **fund-flow / market-signals** 与 **stock-planner** 的桥梁。从CSV数据中根据技术面、资金面、基本面条件筛选股票，并提供综合评分排序。

### 解决的问题
- 跑完资金面和技术面分析后，如何快速从几十只股票中定位优质候选？
- 如何对候选池做客观的综合评分排序？
- 筛选结果如何直接输入 stock-planner 生成交易计划？



### 端到端工作流

每天开盘前，这套工具链可以跑一个完整流程：

```
┌──────────────────────────────────────────────────────────┐
│                  1. 大盘诊断                              │
│  market-sentiment analyze --file market.csv              │
│  └─ 输出市场状态(strong/oscillate/weak/bear)             │
├──────────────────────────────────────────────────────────┤
│                  2. 市场扫描                              │
│  fund-flow --file stocks.csv --trend       ← 资金面      │
│  market-signals --file stocks.csv --scan   ← 技术面      │
├──────────────────────────────────────────────────────────┤
│                  3. 🔎 多因子选股 (本工具)                │
│  stock-screener filter --file stocks.csv ← 条件筛选      │
│  stock-screener rank --file filtered.csv  ← 综合评分排序 │
│  └─ 输出候选池 CSV (可直接输入 stock-planner)            │
├──────────────────────────────────────────────────────────┤
│                  4. 交易计划                              │
│  stock-planner --positions candidates.csv \              │
│    --market strong    ← 来自 market-sentiment 的输出     │
├──────────────────────────────────────────────────────────┤
│                  5. 复盘分析                              │
│  backtest-analyzer --file trades.csv  ← 策略回测         │
│  trade-tracker --file trades.csv     ← 实盘归因          │
└──────────────────────────────────────────────────────────┘
```


## 安装

```bash
# 无外部依赖，Python 3.8+ 即可运行
git clone <repo-url>
cd stock-screener
```

## 子命令

### filter — 多条件筛选
支持 RSI、均线信号、量比、主力资金、PE、PB、价格、市值、涨跌幅等条件同时过滤。

```bash
# 基本面偏好：低估值+温和上涨
python3 scripts/screener.py filter --file stocks.csv \
  --pe-min 5 --pe-max 25 --pb-min 0.5 --pb-max 3 \
  --change-min -3 --change-max 3

# 技术面偏好：RSI适中+放量+均线多头
python3 scripts/screener.py filter --file stocks.csv \
  --rsi-min 40 --rsi-max 60 --volume-ratio-min 1.2 --ma-signal bullish
```

### rank — 综合评分排序
默认技术面40% + 资金面30% + 基本面30%，可自定义权重。

```bash
# 默认权重排序
python3 scripts/screener.py rank --file stocks.csv

# 自定义权重（更重基本面）
python3 scripts/screener.py rank --file stocks.csv \
  --weight-tech 0.2 --weight-fund 0.3 --weight-basic 0.5

# 保存结果
python3 scripts/screener.py rank --file stocks.csv --output ranked.csv
```

### score — 单只股票明细评分
展示指定股票的完整评分卡，包含各维度分数和原始数据。

```bash
python3 scripts/screener.py score --file stocks.csv --code 600519
```

### summary — 数据摘要统计
查看股票池整体状况：各指标分布、均值统计、Top/Bottom 5排名。

```bash
python3 scripts/screener.py summary --file stocks.csv
```

### correlation — 因子相关性分析
计算各因子间的 Pearson 相关系数，发现哪些指标之间存在强关联。

```bash
python3 scripts/screener.py correlation --file stocks.csv
```

## 完整工作流示例

```bash
# Step 0: 大盘情绪诊断 → 确定市场状态
python3 ../market-sentiment/scripts/sentiment.py analyze --file market.csv
# 输出示例: "市场状态: weak (42分)" → 对应 stock-planner --market weak

# Step 1: 技术信号扫描
python3 ../market-signals/scripts/market_signals.py --file stocks.csv --scan

# Step 2: 资金流向分析
python3 ../fund-flow/scripts/fundflow.py --file stocks.csv --trend

# Step 3: 多因子筛选（结合技术面 + 资金面 + 基本面）
python3 scripts/screener.py filter --file stocks.csv \
  --rsi-min 30 --rsi-max 70 --volume-ratio-min 1.0 \
  --fundflow-min 500000 --ma-signal bullish \
  --output filtered.csv

# Step 4: 综合评分排序
python3 scripts/screener.py rank --file filtered.csv \
  --output candidates.csv

# Step 5: 生成交易计划（市场状态来自 Step 0）
python3 ../stock-planner/scripts/stock_planner.py \
  --positions candidates.csv --market weak
```## 评分模型说明

| 维度 | 权重 | 子因子 | 评分逻辑 |
|------|------|--------|----------|
| 技术面 | 40% | RSI (35%) | <30超卖加分, >70超买减分 |
| | | 均线信号 (35%) | bullish/金叉=85, bearish/死叉=15 |
| | | 量比 (30%) | >2.0放量加分, <0.5缩量减分 |
| 资金面 | 30% | 主力资金 (100%) | 基于全体百分位排名 |
| 基本面 | 30% | PE (35%) | <10=85, 10-20=75, >50减分 |
| | | PB (30%) | <1=90, 1-2=75, >5减分 |
| | | 涨跌幅 (35%) | 1-3%温和上涨最佳 |

### 评分解读

| 总分范围 | 建议 |
|----------|------|
| ≥80 | 强烈关注 |
| 65-79 | 关注 |
| 50-64 | 观望 |
| 35-49 | 谨慎 |
| <35 | 回避 |

## 数据格式

输入CSV示例（列名自动识别，支持中英文）：

```
code,name,price,RSI,ma_signal,volume_ratio,main_flow,PE,PB,market_cap,change_pct
600519,贵州茅台,1890.5,55,bullish,1.8,25000000,35.2,8.5,2375000000000,1.2
000858,五粮液,158.3,48,neutral,1.2,8500000,22.1,5.8,614500000000,-0.5
```

## 法律声明

本工具仅为辅助分析参考，不构成任何投资建议。数据来源于用户输入，所有筛选和评分结果仅供进一步分析使用。投资有风险，入市需谨慎。过往表现不代表未来收益。

## License

MIT
