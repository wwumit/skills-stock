# Changelog


## [1.0.2] — 2026-07-19

### Fixed
- 对齐 SKILL.md/README.md/package.json 各文件的版本号

## [1.0.1] — 2026-07-19

### Added
- 端到端工作流图：大盘诊断 → 市场扫描 → 多因子选股 → 交易计划 → 复盘分析
- 完整工作流示例中包含 market-sentiment 的情绪输出接入

## [1.0.0] — 2026-07-19

### Added
- filter 命令：多条件筛选
- rank 命令：多维加权评分排序
- score 命令：单只股票详细评分卡
- summary 命令：数据摘要统计
- correlation 命令：因子相关性矩阵
- 列名自动识别（支持中英文 15+ 种别名）
- CSV输出兼容 stock-planner 格式
- 综合评分建议标签

### Technical
- 纯 Python 标准库，无外部依赖
- 无 exec/eval/subprocess
- 法律免责声明
