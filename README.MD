# Solana Meme Trading Agent 🚀

> **Risk-First AI Trading Agent for Solana Meme Coins**
> 
> 先风控、再报价、后执行 (Risk First, Then Quote, Then Execute)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hackathon](https://img.shields.io/badge/Hackathon-Solana%20Agent%20Economy-purple.svg)](https://x.com/i/communities/2031959181063049384)

---

## 🎯 项目简介

Solana Meme Trading Agent 是一个**风控优先**的 AI 交易助手，专为 Solana Meme 币设计。通过复合风险评分（0-100）、自动化安全检查和强制人工确认机制，帮助用户在高风险的 Meme 币交易中做出明智决策。

**核心理念：**
- 🔒 **风控优先** - 每笔交易前自动进行安全审计
- 🤖 **AI 驱动** - Deep Agents 编排 3 个专业子代理
- ✅ **人工确认** - 强制 "YES" 确认才能执行交易
- ⛽ **Gasless 模式** - 支持免 Gas 费跨链交易（Bitget Wallet）

---

## ✨ 核心功能

### 1. 复合风险评分系统
```
Risk Score = (Security × 0.5) + (Liquidity × 0.3) + (Transaction × 0.2)

阈值：
- SAFE (≥70):    ✅ 安全可交易
- CAUTION (40-69): ⚠️ 需谨慎
- DANGEROUS (<40): ❌ 自动阻止
```

### 2. 四步交易工作流
```
Step 1: 风险预检 → Step 2: 获取报价 → Step 3: 用户确认 ("YES") → Step 4: 执行交易
```

### 3. CLI 命令行界面
```bash
# 扫描热门币种
meme-agent scan --limit 10 --min-score 50

# 检查代币风险
meme-agent risk-check --chain sol --contract EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

# 交互式交易
meme-agent swap --chain sol --from SOL --to USDC --amount 0.1

# 查看钱包余额
meme-agent portfolio
```

### 4. Agent Skills 规范
遵循 [Agent Skills Specification](https://agentskills.io) 标准，支持渐进式披露：
- 4 个自定义技能（SKILL.md）
- 每个技能包含完整文档、脚本和测试
- 兼容 40+ AI Agent 平台（Claude Code, Cursor, OpenClaw 等）

---

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                   CLI Entry Point                       │
│         (Natural Language Input Parsing)                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              TradingAgent (AI Orchestrator)             │
│         Powered by Deep Agents / LangChain              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌────────────┬──────────────┬────────────────┬────────────┐
│   Tools    │  Subagents   │    Skills      │   LLM API  │
│ (5 个工具)  │  (3 个专业 AI) │  (4 个技能文档)  │ (DashScope)│
├────────────┼──────────────┼────────────────┼────────────┤
│ risk_score │ RISK_ANALYST │ risk-scorer    │ qwen3.5+   │
│ scan_memes │ MEME_FINDER  │ wallet-manager │ (OpenAI    │
│ execute    │ TRADE_EXEC   │ meme-scanner   │ Compatible)│
│ portfolio  │              │ trade-executor │            │
└────────────┴──────────────┴────────────────┴────────────┘
```

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Windows / macOS / Linux
- 网络连接（访问 Bitget Wallet API）

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/YOUR_USERNAME/solana-meme-agent.git
cd solana-meme-agent

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API 密钥和钱包配置

# 4. 测试安装
python -m cli.main --help
```

### 配置 .env

```bash
# LLM API (OpenAI 兼容模式 - 推荐)
OPENAI_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
OPENAI_API_KEY=sk-your-api-key
OPENAI_MODEL=qwen3.5-plus

# Solana RPC
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# 钱包配置（测试用）
MNEMONIC_PHRASE=abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about

# 交易参数
DEFAULT_SLIPPAGE=1.0
MIN_LIQUIDITY_USD=10000
MIN_RISK_SCORE=50
```

---

## 📚 使用示例

### 1. 扫描安全 Meme 币

```bash
python -m cli.main scan --limit 5 --min-liquidity 10000 --min-score 70
```

**输出示例：**
```
=== Trending Meme Coins (Risk-Filtered) ===
Rank | Symbol | Price Change | Liquidity  | Holders | Risk Score | Adjusted
-----+--------+--------------+------------+---------+------------+----------
   1 | DOGE2  |        +45.2% |       $50K |     234 |         85 |     38.4
   2 | PEPE3  |        +32.1% |       $25K |     189 |         72 |     23.1

🔍 Scanned: 50 coins | 🟢 Passed: 5 | 🔴 Filtered: 45
```

### 2. 检查代币风险

```bash
python -m cli.main risk-check --chain sol --contract EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
```

**输出示例：**
```
Risk Score: 85/100 (SAFE)
Chain: sol
Contract: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

Breakdown:
  Security:    90/100
  Liquidity:   75/100
  Tx Score:    80/100

Recommendation: SAFE_TO_TRADE
```

### 3. 执行交易

```bash
python -m cli.main swap --chain sol --from SOL --to USDC --amount 0.1
```

**交互流程：**
```
=== TRADE CONFIRMATION ===
From: 0.1 SOL
To:   15.23 USDC (estimated)
Slippage: 1.0%
Risk Score: 85/100 (SAFE)

Type 'YES' to confirm, anything else to cancel: YES

✅ Transaction submitted
TX Hash: 5KtP...
```

---

## 🧪 测试

```bash
# 运行测试套件
pytest

# 运行覆盖率测试
pytest --cov=agent --cov=cli --cov=skills --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

---

## 📁 项目结构

```
solana-meme-agent/
├── cli/                        # CLI 命令行界面
│   ├── __init__.py
│   └── main.py                 # 主入口 (979 lines)
├── agent/                      # AI Agent 编排层
│   └── trading_agent.py        # Deep Agents 配置 (613 lines)
├── skills/                     # Agent Skills (4 个自定义技能)
│   ├── risk-scorer-skill/      # 风险评分技能
│   ├── wallet-manager-skill/   # 钱包管理技能
│   ├── meme-scanner-skill/     # Meme 币发现技能
│   └── trade-executor-skill/   # 交易执行技能
├── tests/                      # 测试套件
│   ├── conftest.py             # Pytest fixtures
│   └── test_placeholder.py     # 基础测试
├── .env.example                # 环境变量模板
├── requirements.txt            # Python 依赖
├── pyproject.toml             # 项目配置
└── README.md                   # 本文件
```

---

## 🛡️ 安全说明

### 密钥管理

- ✅ **助记词存储**：使用系统密钥环（keyring）
- ✅ **私钥衍生**：BIP-44 路径，按需衍生，用后即弃
- ❌ **绝不提交**：`.env`、`*.key`、`mnemonic.txt` 已被 .gitignore 保护

### 交易安全

- ✅ **风控预检**：分数 < 40 自动阻止
- ✅ **人工确认**：必须输入 "YES" 才能执行
- ✅ **Gasless 模式**：默认使用，降低 Gas 风险
- ✅ **模拟交易**：支持 Helius 模拟，提前发现错误

### API 安全

- ✅ **Demo Keys**：内置 Bitget 演示密钥（只读）
- ✅ **环境变量**：支持自定义 API 密钥
- ✅ **无数据收集**：不上传任何用户数据

---

## 🏆 黑客松提交

本项目参加 **Solana Agent Economy Hackathon 2026** (Agent Talent Show)

**赛道：** Bitget Wallet - Solana Meme Coin AI Trading Agent

**提交材料：**
- ✅ 公开代码仓库（GitHub）
- ✅ 在线演示/录屏
- ✅ 可量化结果（风险评分、测试覆盖率）
- ✅ X Article + Quote RT

**标签：** #AgentTalentShow @trendsdotfun @solana_devs @BitgetWallet

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🔗 相关链接

- [Bitget Wallet API 文档](https://web3.bitget.com/en/docs)
- [Agent Skills Specification](https://agentskills.io/specification)
- [Deep Agents Framework](https://github.com/langchain-ai/deepagents)
- [DashScope 阿里云百炼](https://help.aliyun.com/zh/model-studio)
- [RugCheck API](https://api.rugcheck.xyz/v1)

---

## 📞 联系方式

- **GitHub Issues**: [提交问题](https://github.com/YOUR_USERNAME/solana-meme-agent/issues)
- **X (Twitter)**: [@YourHandle](https://x.com/YourHandle)
- **Hackathon Submission**: [X Article Link](https://x.com/your-article-url)

---

<div align="center">

**Built with ❤️ for the Solana Agent Economy Hackathon 2026**

[Report Bug](https://github.com/YOUR_USERNAME/solana-meme-agent/issues) · [Request Feature](https://github.com/YOUR_USERNAME/solana-meme-agent/issues) · [Hackathon Page](https://x.com/i/communities/2031959181063049384)

</div>