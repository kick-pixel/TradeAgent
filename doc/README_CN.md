# Solana Meme Trading Agent

<div align="center">

**AI 驱动的 Solana Meme 币自主交易机器人**

[![黑客松](https://img.shields.io/badge/黑客松-Agent%20Talent%20Show-blue)](https://x.com/i/communities/2031959181063049384)
[![赛道](https://img.shields.io/badge/赛道-Bitget%20Wallet-orange)](https://github.com/bitget-wallet-ai-lab/bitget-wallet-skill)
[![状态](https://img.shields.io/badge/状态-生产就绪-green)](.)
[![许可](https://img.shields.io/badge/许可-MIT-yellow)](LICENSE)

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [核心模块](#-核心模块) • [命令行](#-命令行命令) • [使用示例](#-使用示例) • [参赛指南](#-黑客松参赛)

</div>

---

## 🚀 功能特性

| 功能 | 说明 |
|------|------|
| 🛡️ **决策分析** | 每笔交易前自动执行全面风险评估（安全 + 流动性 + 活动度） |
| 🤖 **自动监控** | 自主持仓跟踪，自动执行止盈止损 |
| 🎯 **自然语言** | 支持中英文聊天 - 智能意图识别 |
| 🔍 **代币发现** | 扫描热门 Solana Meme 币，实时市场数据 |
| 🧠 **AI 决策** | LLM 驱动的交易策略，智能风控管理 |
| 💰 **安全执行** | Bitget Wallet API 集成，交易前安全检查 |

---

## 🏆 黑客松就绪

**参赛项目**: [Solana Agent Economy Hackathon: Agent Talent Show](https://x.com/i/communities/2031959181063049384)

| 类别 | 详情 |
|------|------|
| **赛道** | Bitget Wallet - $5,000 USDT 奖池 |
| **评判标准** | 真实交易盈利表现 |
| **状态** | ✅ 生产就绪 - 可立即提交 |

---

## 系统架构

```
┌─────────────────────────────────────────┐
│   自然语言界面                          │
│   (意图识别)                            │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│   LLM Agent (决策制定)                  │
│   - LangGraph + LangChain               │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│   决策分析器 (交易前检查)               │
│   - 安全评分 (40%)                      │
│   - 流动性评分 (30%)                    │
│   - 活动度评分 (30%)                    │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│   Skills (能力模块)                     │
│   - 扫描器、风险评分、策略              │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│   Bitget Wallet API (执行)              │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│   持仓监控器 (自动卖出)                 │
│   - 止损：-15%                          │
│   - 止盈：+30%                          │
│   - 时间限制：24 小时                   │
└─────────────────────────────────────────┘
```

---

## ⚡ 快速开始

### 前置要求

- Python 3.9+
- LLM API 密钥（OpenAI / Qwen / 等）
- Solana 钱包（助记词）

### 1. 安装依赖

```bash
git clone <仓库地址>
cd BestTradeAgent
pip install -r requirements.txt
```

### 2. 配置环境

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# LLM 配置（Qwen 示例）
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=sk-your-dashscope-key
OPENAI_MODEL=qwen-plus

# 钱包配置
MNEMONIC_PHRASE=你的十二个单词助记词

# 交易参数（可选）
MIN_RISK_SCORE=60
MIN_LIQUIDITY_USD=10000
STOP_LOSS_PCT=15
TAKE_PROFIT_PCT=30
```

### 3. 初始化机器人

```bash
python -m cli.main init
```

### 4. 开始交易

```bash
# 交互式聊天（推荐）
python -m cli.main chat

# 启动持仓监控
python -m cli.main monitor

# 自动投资（带分析）
python -m cli.main auto-invest --budget 10 --no-dry-run
```

---

## 🧠 核心模块

### 1. 决策分析器 (`agent/decision.py`)

**每笔买入前自动执行的全面分析：**

| 组件 | 权重 | 检查项 |
|------|------|--------|
| 安全评分 | 40% | 蜜罐、税率、合约、权限 |
| 流动性评分 | 30% | LP 价值、锁仓比例 |
| 活动度评分 | 30% | 交易量、买卖比例 |

**输出结果：**
- 风险等级：低 / 中 / 高 / 非常高
- 建议：买入 / 观望 / 避免
- 信心度：0-100%

**示例输出：**
```
📊 代币分析报告：PEPE
═══════════════════════════════════════════
🔗 合约：7xKX...
💰 价格：$0.00001234
📈 24h 涨跌：+25.50%

🛡️ 安全评分：85/100 ✅
   • 蜜罐：✅ 否
   • 买入税：0%
   • 卖出税：0%

💧 流动性评分：70/100 ✅
   • 流动性：$150,000

📊 活动度评分：65/100 ✅
   • 24h 交易量：$500,000
   • 买家：1,250 | 卖家：980

💡 建议：🟢 买入
📊 信心度：85%
✅ 分析通过 - 准备执行
```

### 2. 持仓监控器 (`agent/monitor.py`)

**自主持仓管理：**

- 每 60 秒检查一次（可配置）
- 触发条件自动卖出
- 更新状态并记录盈亏

**触发条件：**
| 条件 | 默认值 | 操作 |
|------|--------|------|
| 止盈 | +30% | 全部卖出 |
| 止损 | -15% | 全部卖出 |
| 时间限制 | 24 小时 | 全部卖出 |

```bash
# 持续监控
python -m cli.main monitor

# 检查一次（不循环）
python -m cli.main monitor --once

# 自定义间隔
python -m cli.main monitor --interval 30
```

### 3. 意图识别 (`agent/intent.py`)

**自然语言处理交易命令：**

- 支持中英文
- 自动提取参数
- 映射到结构化操作

**示例：**
```
"buy PEPE with 0.1 SOL"        → 买入 (token=PEPE, amount=0.1)
"卖出 position abc123"          → 卖出 (position_id=abc123)
"扫描热门代币"                  → 扫描 (limit=5)
"analyze 7xKX..."              → 分析 (contract=7xKX...)
"auto invest 20 USDT"          → 自动投资 (budget=20)
```

---

## 💻 命令行命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `chat` | 交互式交易聊天 | `python -m cli.main chat` |
| `monitor` | 自动持仓监控 | `python -m cli.main monitor` |
| `scan` | 扫描热门代币 | `python -m cli.main scan` |
| `analyze` | 深度代币分析 | `python -m cli.main analyze <合约>` |
| `status` | 投资组合状态 | `python -m cli.main status` |
| `positions` | 当前持仓 | `python -m cli.main positions` |
| `auto-invest` | 自动投资（带分析） | `python -m cli.main auto-invest --budget 10` |
| `balance` | 钱包余额 | `python -m cli.main balance` |
| `set-wallet` | 设置钱包地址 | `python -m cli.main set-wallet <地址>` |
| `trade` | 手动交易 | `python -m cli.main trade --from SOL --to <代币>` |
| `close` | 关闭持仓 | `python -m cli.main close <持仓 ID>` |
| `init` | 初始化机器人 | `python -m cli.main init` |

---

## 📊 使用示例

### Chat 模式 + 决策分析

```bash
$ python -m cli.main chat
```

**交互示例：**
```
🟢 Solana Meme 交易机器人
  支持的自然语言命令：
  • buy <代币> with <金额> SOL
  • sell <持仓 ID>
  • scan / 扫描
  • analyze <代币>
  • status / 状态
  • positions / 持仓

你：buy PEPE with 0.05 SOL
识别意图：买入 PEPE 用 0.05 SOL

准备买入 PEPE 用 0.05 SOL
正在执行自动决策分析...

📊 代币分析报告：PEPE
═══════════════════════════════════════════
🛡️ 安全评分：85/100 ✅
💧 流动性评分：70/100 ✅
📈 活动度评分：65/100 ✅

💡 建议：🟢 买入
📊 信心度：85%

✅ 分析通过：综合评分良好
确认执行买入？[y/N]: y

[买入执行成功]
代币：PEPE
数量：1000000
入场价：$0.00005
止损价：$0.0000425 (-15%)
止盈价：$0.000065 (+30%)
```

### 自动监控实战

```bash
$ python -m cli.main monitor
```

**输出示例：**
```
🚀 持仓监控已启动
⏱️  检查间隔：60 秒
🎯 止盈：+30% | 止损：-15%
⏰ 最大持仓：24 小时

📊 [14:32:10] 检查 2 个持仓...
📈 PEPE: $0.00000012 (+20.0%) | 持仓：2.5h
📈 DOGE: $0.00000013 (+30.0%) | 持仓：1.2h

⚡ 触发卖出：DOGE - 止盈触发
💰 预计获得：0.128 SOL
✅ 卖出成功：DOGE
🟢 盈亏：+$3.20 (+30.0%)
```

---

## 🛡️ 风险管理

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 最大仓位 | 5% | 每笔交易上限 |
| 每日交易 | 5 次 | 每日交易限制 |
| 最大持仓 | 3 个 | 同时持仓数 |
| 最低风险分 | 50 | 最低安全评分 |
| 最低流动性 | $10,000 | 最低 LP 价值 |
| 止损 | -15% | 自动卖出触发 |
| 止盈 | +30% | 自动卖出触发 |
| 最大持仓时间 | 24h | 时间限制卖出 |

---

## 🔒 安全特性

1. **交易前分析**: 每笔买入都执行全面风险评估
2. **人工确认**: 所有交易需要用户明确确认
3. **安全检查**: 自动蜜罐和风险检测
4. **安全密钥存储**: 助记词按需派生，永不存储
5. **持仓追踪**: 完整交易历史和盈亏记录
6. **自动风控**: 止盈止损自动监控执行

---

## 📁 项目结构

```
BestTradeAgent/
├── agent/
│   ├── core.py                 # LLM 机器人和工具
│   ├── state.py                # 状态管理
│   ├── config.py                # 配置管理
│   ├── wallet.py               # 钱包管理
│   ├── monitor.py              # 持仓监控 ⭐
│   ├── decision.py             # 决策分析 ⭐
│   └── intent.py               # 意图识别 ⭐
├── cli/
│   └── main.py                 # CLI 入口
├── skills/
│   ├── bitget-wallet-skill/    # 交易执行
│   ├── meme-scanner-skill/     # 代币扫描
│   ├── risk-scorer-skill/      # 风险评估
│   └── trading-strategy-skill/ # 策略指导
├── tests/
│   └── test_config.py
├── doc/
│   └── DEMAND.md               # 黑客松要求
├── README.md                   # 英文版
├── README_CN.md                # 中文版（本文件）
└── HACKATHON_SUBMISSION.md     # 提交指南
```

---

## 🏆 黑客松参赛

**比赛名称**: [Solana Agent Economy Hackathon: Agent Talent Show](https://x.com/i/communities/2031959181063049384)

| 类别 | 详情 |
|------|------|
| **赛道** | Bitget Wallet - $5,000 USDT |
| **奖金** | 第 1 名：$2,500 / 第 2 名：$1,500 / 第 3 名：$1,000 |
| **评判** | 真实交易盈利表现 |
| **状态** | ✅ 完成并可提交 |

### 提交检查清单

- [ ] 代码仓库公开
- [ ] README 已更新
- [ ] 演示视频已录制
- [ ] X Article 已发布
- [ ] Quote RT @trendsdotfun @solana_devs @BitgetWallet
- [ ] 话题标签：#AgentTalentShow

详细指南见 [HACKATHON_SUBMISSION.md](HACKATHON_SUBMISSION.md)

---

## 📄 许可

MIT License - 详见 [LICENSE](LICENSE) 文件。

---

<div align="center">

**用 ❤️ 为 Solana 生态构建**

[报告问题](../../issues) • [请求功能](../../issues) • [参赛指南](HACKATHON_SUBMISSION.md)

</div>
