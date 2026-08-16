<!-- wwumit brand header: governance-driven AI skills ecosystem -->
<p align="center"><b>wwumit</b> · 治理驱动的 AI 技能生态 — 规则 → 检查 → 评分 → 报告</p>
<p align="center">产品线：<a href="https://github.com/wwumit/skills-compliance-intl">合规（compliancehub）</a> · <a href="https://github.com/wwumit/skills-stock">股票</a> · <a href="https://github.com/wwumit/skills-tools">工具</a> · 插件 <a href="https://github.com/wwumit/dsh-compliancehub">dsh-compliancehub</a> · 数据层 <a href="https://github.com/wwumit/skills-catalog">catalog</a></p>
<hr>

# Skills Stock

## Skills

| Skill | Description | Version |
|---|---|---|
| `backtest-analyzer` | 回测分析工具。从交易记录CSV计算回测核心指标： | 1.0.0 |
| `fund-flow` | 资金流向分析工具 v1.1.0。分析股票/板块的主力资金净流入排行、 | 1.1.0 |
| `market-sentiment` | 四维度市场情绪评估（情绪/趋势/量能/宽度极端度），对大盘环境诊断并输出 0–100 评分与对应市场状态。 | 1.1.0 |
| `market-signals` | 技术信号扫描器 v1.1.0。从价格数据计算RSI(14)、均线(5/10/20)、 | 1.1.0 |
| `stock-planner` | 交易计划生成器。基于当前持仓、市场状态和策略规则 | 1.0.0 |
| `stock-screener` | 🔎 多因子选股器 v1.0.2。连接 fund-flow / market-signals → stock-planner 的桥梁。 | 1.0.2 |
| `trade-tracker` | 交易追踪与归因分析 v1.1.0。从交易记录逐笔追踪盈亏、 | 1.1.0 |

## Install

```bash
# Install one skill (skills.sh CLI)
npx skills add wwumit/skills-stock --skill <name>

# Install all skills in this repo
npx skills add wwumit/skills-stock --all
```

Skills are also compatible with DeepSeek Harness (DSH): copy the skill directory into
`~/.dsh/skills/` or `<project>/.dsh/skills/` and it is auto-discovered.

## License

MIT
