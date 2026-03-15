# Solana Meme Trading Agent

<div align="center">

**AI-Powered Autonomous Trading Agent for Solana Meme Coins**

[![Hackathon](https://img.shields.io/badge/Hackathon-Agent%20Talent%20Show-blue)](https://x.com/i/communities/2031959181063049384)
[![Track](https://img.shields.io/badge/Track-Bitget%20Wallet-orange)](https://github.com/bitget-wallet-ai-lab/bitget-wallet-skill)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-green)](.)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

[Features](#-features) • [Quick Start](#-quick-start) • [Core Modules](#-core-modules) • [CLI Commands](#-cli-commands) • [Examples](#-examples) • [Hackathon](#-hackathon-submission)

</div>

---

## 🚀 Features

| Feature | Description |
|---------|-------------|
| 🛡️ **Decision Analysis** | Comprehensive risk assessment before EVERY trade (Security + Liquidity + Activity) |
| 🤖 **Auto Monitoring** | Autonomous position tracking with automatic stop-loss/take-profit execution |
| 🎯 **Natural Language** | Chat in English or Chinese - intelligent intent recognition |
| 🔍 **Token Discovery** | Scan trending Solana meme coins with real-time market data |
| 🧠 **AI Decision Making** | LLM-powered trading strategy with risk management |
| 💰 **Safe Execution** | Bitget Wallet API integration with pre-trade security checks |

---

## 🏆 Hackathon Ready

**Built for**: [Solana Agent Economy Hackathon: Agent Talent Show](https://x.com/i/communities/2031959181063049384)

| Category | Details |
|----------|---------|
| **Track** | Bitget Wallet - $5,000 USDT Prize Pool |
| **Judging** | Real trading profit performance |
| **Status** | ✅ Production Ready - Ready to Submit |

---

## Architecture

```
┌─────────────────────────────────────────┐
│   Natural Language Interface            │
│   (Intent Recognition)                  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│   LLM Agent (Decision Making)           │
│   - LangGraph + LangChain               │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│   Decision Analyzer (Pre-trade Check)   │
│   - Security Score (40%)                │
│   - Liquidity Score (30%)               │
│   - Activity Score (30%)                │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│   Skills (Capabilities)                 │
│   - Scanner, Risk Scorer, Strategy      │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│   Bitget Wallet API (Execution)         │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│   Position Monitor (Auto-sell)          │
│   - Stop Loss: -15%                     │
│   - Take Profit: +30%                   │
│   - Time Limit: 24h                     │
└─────────────────────────────────────────┘
```

---

## ⚡ Quick Start

### Prerequisites

- Python 3.9+
- LLM API Key (OpenAI / Qwen / etc.)
- Solana Wallet (mnemonic phrase)

### 1. Install Dependencies

```bash
git clone <repository-url>
cd BestTradeAgent
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# LLM Configuration (Qwen example)
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=sk-your-dashscope-key
OPENAI_MODEL=qwen-plus

# Wallet Configuration
MNEMONIC_PHRASE=your-twelve-word-mnemonic

# Trading Parameters (optional)
MIN_RISK_SCORE=60
MIN_LIQUIDITY_USD=10000
STOP_LOSS_PCT=15
TAKE_PROFIT_PCT=30
```

### 3. Initialize Agent

```bash
python -m cli.main init
```

### 4. Start Trading

```bash
# Interactive chat (recommended)
python -m cli.main chat

# Start position monitoring
python -m cli.main monitor

# Auto-invest with analysis
python -m cli.main auto-invest --budget 10 --no-dry-run
```

---

## 🧠 Core Modules

### 1. Decision Analyzer (`agent/decision.py`)

**Pre-trade analysis that runs automatically before every buy:**

| Component | Weight | Checks |
|-----------|--------|--------|
| Security Score | 40% | Honeypot, Taxes, Contract, Permissions |
| Liquidity Score | 30% | LP Value, Locked Percentage |
| Activity Score | 30% | Volume, Buyers/Sellers Ratio |

**Output:**
- Risk Level: LOW / MEDIUM / HIGH / VERY_HIGH
- Recommendation: BUY / WATCH / AVOID
- Confidence Score: 0-100%

**Example Output:**
```
📊 Token Analysis Report: PEPE
═══════════════════════════════════════════
🔗 Contract: 7xKX...
💰 Price: $0.00001234
📈 24h Change: +25.50%

🛡️ Security Score: 85/100 ✅
   • Honeypot: ✅ No
   • Buy Tax: 0%
   • Sell Tax: 0%

💧 Liquidity Score: 70/100 ✅
   • Liquidity: $150,000

📊 Activity Score: 65/100 ✅
   • 24h Volume: $500,000
   • Buyers: 1,250 | Sellers: 980

💡 Recommendation: 🟢 BUY
📊 Confidence: 85%
✅ Analysis PASSED - Ready to execute
```

### 2. Position Monitor (`agent/monitor.py`)

**Autonomous position management:**

- Checks every 60 seconds (configurable)
- Auto-sells on trigger conditions
- Updates state and records PnL

**Trigger Conditions:**
| Condition | Default | Action |
|-----------|---------|--------|
| Take Profit | +30% | Sell all |
| Stop Loss | -15% | Sell all |
| Time Limit | 24 hours | Sell all |

```bash
# Start continuous monitoring
python -m cli.main monitor

# Check once (no continuous loop)
python -m cli.main monitor --once

# Custom interval
python -m cli.main monitor --interval 30
```

### 3. Intent Recognition (`agent/intent.py`)

**Natural language processing for trading commands:**

- Supports English and Chinese
- Extracts parameters automatically
- Maps to structured actions

**Examples:**
```
"buy PEPE with 0.1 SOL"        → BUY(token=PEPE, amount=0.1)
"卖出 position abc123"          → SELL(position_id=abc123)
"扫描热门代币"                  → SCAN(limit=5)
"analyze 7xKX..."              → ANALYZE(contract=7xKX...)
"auto invest 20 USDT"          → AUTO_INVEST(budget=20)
```

---

## 💻 CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `chat` | Interactive trading chat | `python -m cli.main chat` |
| `monitor` | Auto position monitoring | `python -m cli.main monitor` |
| `scan` | Scan trending tokens | `python -m cli.main scan` |
| `analyze` | Deep token analysis | `python -m cli.main analyze <contract>` |
| `status` | Portfolio status | `python -m cli.main status` |
| `positions` | Open positions | `python -m cli.main positions` |
| `auto-invest` | Auto invest with analysis | `python -m cli.main auto-invest --budget 10` |
| `balance` | Wallet balance | `python -m cli.main balance` |
| `set-wallet` | Set wallet address | `python -m cli.main set-wallet <addr>` |
| `trade` | Manual trade | `python -m cli.main trade --from SOL --to <token>` |
| `close` | Close position | `python -m cli.main close <position_id>` |
| `init` | Initialize agent | `python -m cli.main init` |

---

## 📊 Examples

### Chat Mode with Decision Analysis

```bash
$ python -m cli.main chat
```

**Sample Interaction:**
```
🟢 Solana Meme Trading Agent
  Natural language commands supported:
  • buy <token> with <amount> SOL
  • sell <position_id>
  • scan / 扫描
  • analyze <token>
  • status / 状态
  • positions / 持仓

You: buy PEPE with 0.05 SOL
识别意图：买入 PEPE 用 0.05 SOL

准备买入 PEPE 用 0.05 SOL
正在执行自动决策分析...

📊 代币分析报告：PEPE
═══════════════════════════════════════════
🛡️ 安全评分：85/100 ✅
💧 流动性评分：70/100 ✅
📈 活动评分：65/100 ✅

💡 建议：🟢 买入
📊 信心度：85%

✅ 分析通过：综合评分良好
确认执行买入？[y/N]: y

[BUY EXECUTED SUCCESSFULLY]
Token: PEPE
Amount: 1000000
Entry Price: $0.00005
Stop Loss: $0.0000425 (-15%)
Take Profit: $0.000065 (+30%)
```

### Auto-Monitoring in Action

```bash
$ python -m cli.main monitor
```

**Sample Output:**
```
🚀 Position Monitor Starting
⏱️  Check Interval: 60s
🎯 Take Profit: +30% | Stop Loss: -15%
⏰ Max Hold: 24h

📊 [14:32:10] Checking 2 positions...
📈 PEPE: $0.00000012 (+20.0%) | Hold: 2.5h
📈 DOGE: $0.00000013 (+30.0%) | Hold: 1.2h

⚡ SELL TRIGGERED: DOGE - Take Profit
💰 Expected: 0.128 SOL
✅ Sell SUCCESS: DOGE
🟢 PnL: +$3.20 (+30.0%)
```

---

## 🛡️ Risk Management

| Parameter | Default | Description |
|-----------|---------|-------------|
| Max Position | 5% | Maximum per trade |
| Max Daily Trades | 5 | Trades per day limit |
| Max Holdings | 3 | Concurrent positions |
| Min Risk Score | 50 | Minimum safety score |
| Min Liquidity | $10,000 | Minimum LP value |
| Stop Loss | -15% | Auto-sell trigger |
| Take Profit | +30% | Auto-sell trigger |
| Max Hold Time | 24h | Time-based exit |

---

## 🔒 Safety Features

1. **Pre-trade Analysis**: Every buy undergoes comprehensive risk assessment
2. **Human-in-the-loop**: All trades require explicit user confirmation
3. **Security Checks**: Automatic honeypot and risk detection
4. **Secure Key Storage**: Mnemonic derived on-demand, never stored
5. **Position Tracking**: Complete trade history and PnL accounting
6. **Auto Risk Management**: Stop-loss and take-profit automatically monitored

---

## 📁 Project Structure

```
BestTradeAgent/
├── agent/
│   ├── core.py                 # LLM agent and tools
│   ├── state.py                # State management
│   ├── config.py               # Configuration
│   ├── wallet.py               # Wallet management
│   ├── monitor.py              # Position monitor ⭐
│   ├── decision.py             # Decision analyzer ⭐
│   └── intent.py               # Intent recognition ⭐
├── cli/
│   └── main.py                 # CLI entry point
├── skills/
│   ├── bitget-wallet-skill/    # Trading execution
│   ├── meme-scanner-skill/     # Token discovery
│   ├── risk-scorer-skill/      # Risk assessment
│   └── trading-strategy-skill/ # Strategy guidance
├── tests/
│   └── test_config.py
├── doc/
│   └── DEMAND.md               # Hackathon requirements
├── README.md                   # This file (English)
├── README_CN.md                # Chinese version
└── HACKATHON_SUBMISSION.md     # Submission guide
```

---

## 🏆 Hackathon Submission

**Competition**: [Solana Agent Economy Hackathon: Agent Talent Show](https://x.com/i/communities/2031959181063049384)

| Category | Details |
|----------|---------|
| **Track** | Bitget Wallet - $5,000 USDT |
| **Prizes** | 1st: $2,500 / 2nd: $1,500 / 3rd: $1,000 |
| **Judging** | Real trading profit performance |
| **Status** | ✅ Complete and Ready to Submit |

### Submission Checklist

- [ ] Code repository public
- [ ] README updated
- [ ] Demo video recorded
- [ ] X Article published
- [ ] Quote RT with @trendsdotfun @solana_devs @BitgetWallet
- [ ] Hashtag: #AgentTalentShow

See [HACKATHON_SUBMISSION.md](HACKATHON_SUBMISSION.md) for detailed guide.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ for the Solana ecosystem**

[Report Bug](../../issues) • [Request Feature](../../issues) • [Hackathon Guide](HACKATHON_SUBMISSION.md)

</div>
