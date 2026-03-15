# Solana Meme Trading Agent

<div align="center">

Natural-language trading copilot for Solana meme tokens, backed by Bitget Wallet market data and execution.

[![Hackathon](https://img.shields.io/badge/Hackathon-Agent%20Talent%20Show-blue)](https://x.com/i/communities/2031959181063049384)
[![Track](https://img.shields.io/badge/Track-Bitget%20Wallet-orange)](https://github.com/bitget-wallet-ai-lab/bitget-wallet-skill)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

[Quick Start](#quick-start) • [What It Can Do](#what-it-can-do) • [Real Examples](#real-examples) • [CLI Commands](#cli-commands) • [Risk & Exit Strategy](#risk--exit-strategy) • [Architecture](#architecture)

</div>

---

## What it can do

This project lets you interact with a Solana meme trading agent in plain language.

Current capabilities:

- scan trending Solana meme tokens
- analyze a token before trading
- buy by mint address or common symbol such as `BONK`
- sell open positions
- show wallet status, balances, positions, and recent trade history
- build a small auto-invest plan from trending opportunities
- monitor open positions continuously and exit automatically based on strategy rules

The agent keeps short multi-turn conversation memory in `.agent/state.json`, so follow-up requests such as `buy it`, `show my status`, or `sell that position` work better than in a stateless CLI.

## Key behaviors

| Capability | Current behavior |
|---|---|
| Natural-language chat | `python -m cli.main chat` accepts free-form requests and falls back to LLM intent classification when regex rules do not match |
| Dedicated trading prompt | The agent uses a Solana meme-specific system prompt with supported workflows and safety rules |
| Conversation memory | Recent chat turns are persisted and reloaded across sessions |
| Symbol resolution | Buy/analyze flows can resolve symbols like `BONK` to a Solana mint before analysis |
| Pre-trade analysis | Every buy runs security, liquidity, and activity checks before execution |
| Weighted auto-invest | Auto-invest allocates budget by score and liquidity instead of equal splits |
| Dynamic exits | Monitor now uses partial take profit, breakeven promotion, trailing stop, time stop, and exit attribution |
| Human confirmation | Live buys, sells, and auto-invest execution still require explicit confirmation |

---

## Quick Start

### Requirements

- Python 3.9+
- an LLM API key compatible with the configured OpenAI-style endpoint
- a Solana wallet mnemonic for live trading or monitoring

### Install

```bash
git clone <repository-url>
cd BestTradeAgent
pip install -r requirements.txt
```

### Configure `.env`

```bash
cp .env.example .env
```

Typical config:

```bash
# LLM
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=qwen-plus

# Wallet
MNEMONIC_PHRASE=your-twelve-word-mnemonic

# Risk settings
MIN_RISK_SCORE=50
MIN_LIQUIDITY_USD=10000
STOP_LOSS_PCT=15
TAKE_PROFIT_PCT=30
MAX_DAILY_TRADES=5
MAX_HOLDINGS=3
```

### Initialize

```bash
python -m cli.main init
```

### Start with chat

```bash
python -m cli.main chat
```

---

## Real Examples

These are trimmed from `doc/result.txt` and reflect real project output.

### 1. CLI help

```text
$ python -m cli.main --help

Commands:
  chat
  scan
  analyze
  status
  positions
  auto-invest
  balance
  set-wallet
  trade
  close
  monitor
  init
```

### 2. Chat entrypoint

```text
$ python -m cli.main chat

Solana Meme Trading Agent
Talk naturally. Try things like:
  - scan hot Solana memes
  - analyze this token 7xKX...
  - buy BONK with 0.05 SOL
  - sell position abc123
  - show my portfolio status
  - auto invest 0.01 SOL
```

### 3. Auto-invest example

```text
You: auto invest 0.01 SOL
Intent: Auto-invest with budget 0.01 SOL (~1.50 USDT)

Found 4 qualified tokens

Investment Plan
1. Rosie  Allocation: $0.06 USDT ~= 0.0004 SOL
2. Punch  Allocation: $0.17 USDT ~= 0.0011 SOL
3. TRUMP  Allocation: $1.27 USDT ~= 0.0085 SOL
Total: $1.50 USDT
```

That example matters because it shows the current implementation is no longer equal-weighted. Higher-scoring, more liquid names receive more capital.

### 4. Monitor strategy summary

```text
$ python -m cli.main monitor

Initial stop loss: -15.0%
Partial take profit: +15.0% (sell 50%)
Breakeven promotion: enabled after partial TP
Trailing stop: 10.0% on remainder
Max hold: 24h
```

---

## Chat Experience

The chat flow is the best way to use the agent.

Example prompts:

```text
scan hot Solana memes
analyze this token 7xKX...
buy BONK with 0.05 SOL
show my portfolio status
sell position abc123
auto invest 0.01 SOL
```

What happens during a buy:

1. the input is parsed into a trading intent
2. if you used a symbol, it is resolved to a Solana mint when possible
3. the agent runs decision analysis
4. you see a report with score, liquidity, and recommendation
5. execution only proceeds after confirmation

If a symbol is ambiguous or cannot be resolved safely, the buy is cancelled with a clear message instead of analyzing fake zero-price data.

---

## CLI Commands

| Command | Purpose | Example |
|---|---|---|
| `chat` | Start the natural-language trading chat | `python -m cli.main chat` |
| `init` | Validate config, skills, wallet, and local state | `python -m cli.main init` |
| `scan` | Scan and summarize trending tokens | `python -m cli.main scan --limit 5` |
| `analyze` | Analyze a specific token contract | `python -m cli.main analyze <contract>` |
| `status` | Show wallet status, PnL, balances, and monitor strategy summary | `python -m cli.main status` |
| `positions` | Show open positions and strategy-aware exit status | `python -m cli.main positions` |
| `auto-invest` | Build a weighted investment plan from trending tokens | `python -m cli.main auto-invest --budget 10 --dry-run` |
| `balance` | Ask the agent for wallet balances | `python -m cli.main balance` |
| `set-wallet` | Persist a wallet address in local state | `python -m cli.main set-wallet <address>` |
| `trade` | Prepare a manual swap flow | `python -m cli.main trade --from SOL --to <token> --amount 0.1` |
| `close` | Close a position by ID | `python -m cli.main close <position_id>` |
| `monitor` | Monitor open positions and auto-sell on dynamic triggers | `python -m cli.main monitor --interval 60` |

### Notes

- `chat` supports symbol-based buys like `buy BONK with 0.05 SOL`.
- `analyze` and `trade` still work best with explicit contracts.
- `auto-invest` CLI mode takes a USDT budget, while chat mode can understand `SOL` or `USDT` phrasing.
- `positions` and sell previews now show strategy-aware exit text such as `initial SL`, `partial TP`, `breakeven armed`, and `trailing`.
- `history` now includes exit attribution such as `partial take profit`, `trailing stop`, `stop loss`, or `time stop`.

---

## Risk & Exit Strategy

The project started with simple fixed exits, but the current monitor is more dynamic.

### Portfolio-level controls

| Rule | Default |
|---|---|
| Max position size | 5% of portfolio value per trade |
| Max daily trades | 5 |
| Max concurrent holdings | 3 |
| Min liquidity | $10,000 |
| Min risk score | 50 / 100 |

### Position-level exit strategy

| Stage | Default behavior |
|---|---|
| Initial stop loss | -15% |
| First profit event | +15% partial take profit, sell 50% |
| After partial TP | stop promoted to breakeven |
| Remaining size | 10% trailing stop |
| Time stop | 24h max hold |

Note: the immediate buy execution receipt can still show the initial fixed `Stop Loss` and `Take Profit` prices created at entry time. Once the position is under monitor control, exits follow the dynamic strategy above.

The decision analyzer in `agent/decision.py` scores:

- security: honeypot flags, taxes, permissions
- liquidity: LP depth and minimum thresholds
- activity: recent buyers, sellers, and volume

The monitor in `agent/monitor.py` now also includes:

- duplicate-exit protection via `exit_pending`
- post-trade reconciliation using real order details when available
- restart recovery for pending exits
- exit reason attribution persisted to state and trade history

---

## Architecture

```text
Natural-language chat / CLI
        ↓
Intent recognition + LLM fallback
        ↓
Solana meme trading prompt + conversation memory
        ↓
Decision analyzer (security + liquidity + activity)
        ↓
Bitget-backed market data and execution tools
        ↓
State persistence + monitor + trade history attribution
```

Relevant files:

- `cli/main.py` - chat loop, CLI commands, user-facing flows
- `agent/core.py` - LangGraph/LangChain agent wiring and trading tools
- `agent/prompts.py` - dedicated Solana meme system prompt
- `agent/capabilities.py` - supported workflows and chat examples
- `agent/decision.py` - pre-trade analysis and symbol resolution
- `agent/allocation.py` - weighted auto-invest allocation
- `agent/state.py` - positions, trade history, memory, conversation history
- `agent/monitor.py` - dynamic exit monitoring, reconciliation, recovery
- `agent/position_display.py` - strategy-aware display text and exit labels

---

## Project Structure

```text
BestTradeAgent/
├── agent/
│   ├── allocation.py
│   ├── capabilities.py
│   ├── config.py
│   ├── core.py
│   ├── decision.py
│   ├── monitor.py
│   ├── position_display.py
│   ├── prompts.py
│   └── state.py
├── cli/
│   └── main.py
├── skills/
│   ├── bitget-wallet-skill/
│   ├── meme-scanner-skill/
│   ├── risk-scorer-skill/
│   └── trading-strategy-skill/
├── tests/
│   ├── test_auto_invest_allocation.py
│   ├── test_chat_features.py
│   ├── test_config.py
│   ├── test_monitor_strategy.py
│   └── test_token_resolution.py
├── doc/
│   ├── DEMAND.md
│   ├── README_CN.md
└── README.md
```

---

## Safety Notes

- This project can execute real trades if you confirm them.
- Symbol-based token resolution is best-effort and still safer with an explicit mint.
- Keep your mnemonic secure. The agent uses it for wallet operations.
- Always verify what you are buying, especially for meme tokens with duplicate symbols.

---

## Hackathon Context

This repo was built for the Bitget Wallet track of the Solana Agent Economy Hackathon: Agent Talent Show.

---

## License

MIT. See `LICENSE`.
