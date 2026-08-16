---
name: stock-screener
description: |
  🔎 多因子选股器 v1.0.2。连接 fund-flow / market-signals → stock-planner 的桥梁。
  支持按 RSI、均线信号、量比、主力资金、PE、PB、市值、价格、涨跌幅等条件多因子筛选，
  以及综合评分排序、单股明细分析、因子相关性分析。

  Use when: 需要根据技术面/资金面/基本面条件筛选股票、
  对多股票综合评分排序、因子相关性分析、为交易计划(stock-planner)准备候选池。

  触发关键词：选股、筛选、screener、多因子、scan、multi-factor、因子评分

  数据源兼容性：
  - market-signals 的输出(包含RSI、均线信号、量比等)
  - fund-flow 的输出(包含主力资金流向)
  - 自定义CSV(自动识别中英文列名)
  
  运行模式：纯本地
---

# 🔎 Stock Screener

## Overview
多因子选股器，支持从CSV数据中根据技术面、资金面、基本面条件筛选股票，并输出综合评分。设计为连接 fund-flow / market-signals 与 stock-planner 的桥接工具。

## 5大子命令

| 命令 | 功能 | 适用场景 |
|------|------|----------|
| `filter` | 多条件筛选（RSI、均线、量比、资金、PE/PB、价格、市值等） | 快速定位符合指定条件的股票 |
| `rank` | 多维加权评分排序（技术40%+资金30%+基本面30%） | 对候选池做综合排名 |
| `score` | 单只股票详细评分（含各维度明细） | 深入研究某只个股 |
| `summary` | 数据摘要统计（分布、均值、Top/Bottom 5） | 了解整体池状态 |
| `correlation` | 因子相关性矩阵 | 发现因子间的关联关系 |

## 评分模型

```
综合评分 = 技术面(40%) + 资金面(30%) + 基本面(30%)

技术面 = RSI评分(35%) + 均线信号评分(35%) + 量比评分(30%)
资金面 = 主力资金百分位评分(100%)
基本面 = PE评分(35%) + PB评分(30%) + 涨跌幅评分(35%)
```

## Usage

```bash
# 1. 多条件筛选：RSI 30-70，量比>1.5，主力净流入>0
python3 scripts/screener.py filter --file stocks.csv \
  --rsi-min 30 --rsi-max 70 --volume-ratio-min 1.5 --fundflow-min 0

# 2. 综合评分排序（带权重调节）
python3 scripts/screener.py rank --file stocks.csv \
  --weight-tech 0.4 --weight-fund 0.3 --weight-basic 0.3

# 3. 单只股票明细
python3 scripts/screener.py score --file stocks.csv --code 600519

# 4. 数据摘要
python3 scripts/screener.py summary --file stocks.csv

# 5. 因子相关性分析
python3 scripts/screener.py correlation --file stocks.csv
```

## 工作流示例

### 从技术扫描到交易计划
```bash
# Step 1: 扫描技术信号
python3 scripts/market_signals.py --file portfolio.csv --scan

# Step 2: 用筛选器过滤出优质候选
python3 scripts/screener.py filter --file portfolio.csv \
  --rsi-min 40 --rsi-max 60 --ma-signal bullish --volume-ratio-min 1.2

# Step 3: 评分排序
python3 scripts/screener.py rank --file portfolio.csv --output candidates.csv

# Step 4: 生成交易计划
python3 scripts/stock_planner.py --positions candidates.csv
```

## 列名识别
自动识别中/英文列名，支持以下标准字段：
- 代码: code, stock, symbol, 代码
- RSI: rsi, RSI, rsi_14
- 均线信号: ma_signal, MA信号
- 量比: volume_ratio, 量比
- 主力资金: main_flow, fundflow, 主力净流入
- PE/PB: pe/PE/市盈率, pb/PB/市净率
- 市值: market_cap, mcap, 总市值
- 涨跌幅: change_pct, 涨跌幅

## 输出兼容性
- `filter --output` 输出的CSV可直接用于 stock-planner 的 --positions 参数
- `rank --output` 额外包含评分列，可用于后续分析

## 法律声明
本工具仅为辅助分析参考，不构成任何投资建议。数据来源于用户输入，所有筛选和评分结果仅供进一步分析使用。投资有风险，入市需谨慎。

## 版本历史
- v1.0.0 (2026-07-19): 初始版本，支持filter/rank/score/summary/correlation 5个子命令
