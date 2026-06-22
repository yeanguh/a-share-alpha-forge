---
name: china-stock-price-analysis
description: 通用A股股价查询与估值分析技能，支持通过QVeris获取实时股价，应用相对估值法（PE/PB/PS）进行估值分析。使用当用户询问A股个股股价、估值分析时触发。
---

# A股股价查询与估值分析技能

## 使用方式

### 方式一：脚本自动化分析（推荐）

使用固化的Python脚本自动完成估值计算，准确高效，脚本直接调用QVeris API获取行情：

```bash
# 直接运行，一步到位
python skills/china-stock-price-analysis/scripts/stock_analyze.py 002475.SZ \
  --industry "消费电子龙头" \
  --eps-expected 2.3 \
  --ebitda 260 \
  --net-debt 100 \
  --consensus-target 63
```

也支持从JSON文件读取已有行情数据：
```bash
python skills/china-stock-price-analysis/scripts/stock_analyze.py 002475.SZ \
  --json quote.json \
  --industry "消费电子龙头" \
  --eps-expected 2.3 \
  --consensus-target 63
```

脚本自动完成：
1. 直接调用QVeris API获取最新实时行情
2. PE/PB估值判断，对比行业预设合理区间
3. 业绩预期法计算合理估值区间
4. EV/EBITDA计算（若提供EBITDA数据）
5. 一致性预期上涨空间计算
6. 输出**完整markdown分级结构分析报告**，包含所有计算步骤展示方便核对

### 方式二：手动分析

1. **工具选择**: 优先使用 QVeris 查找A股实时行情工具 `ths_ifind.real_time_quotation.v1`
2. **输入参数**: A股股票代码，格式如 `002475.SZ`、`600519.SH`
3. **结果提取**: 获取最新价、涨跌幅、成交量、成交额等核心数据展示

## 估值分析框架

完整的通用估值方法论请参考 [references/valuation-framework.md](references/valuation-framework.md)

### 核心估值方法

**绝对估值法**:
- **DCF现金流折现法**: 企业价值等于未来自由现金流折现之和，适合现金流稳定可预测的企业
- **EBITDA倍数法**: EV/EBITDA估值，剔除资本结构和折旧摊销影响，适合重资产行业

**相对估值法**：结合PE（市盈率）、PB（市净率）、PS（市销率）三个维度分析
- PE = 股价 / 每股收益 → 判断盈利端估值合理性
- PB = 股价 / 每股净资产 → 判断安全边际
- PS = 股价 / 每股营收 → 判断营收端成长性

**业绩预期法**：结合一致EPS预期 × 行业合理PE区间 = 合理估值中枢

## 使用流程

1. **获取股票代码**：确认用户询问的股票及代码（格式 `.SZ`/`.SH` 后缀）
2. **查询实时行情**：调用QVeris工具获取最新股价
3. **估值分析**：
   - 获取最新财报EPS、BVPS、每股营收数据
   - 计算当前PE/PB/PS
   - 对比行业合理区间，给出低估/合理/高估判断
   - 如有券商一致目标价，计算预期空间

## 行业合理PE参考区间（示例）

| 行业         | 合理PE区间 | 说明                 |
|--------------|-----------|----------------------|
| 消费电子龙头 | 20~30倍   | 立讯精密等成熟龙头   |
| 白酒龙头     | 25~35倍   | 高端白酒确定性溢价   |
| 半导体设备   | 30~45倍   | 高成长行业           |
| 传统制造业   | 10~18倍   | 周期/成熟行业        |

实际分析时，应根据具体行业特性调整合理区间。
