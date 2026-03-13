---
name: trade-executor-skill
description: Execute and manage token trades on Solana DEXs including swap execution, limit orders, position tracking, and P&L calculation. Use when performing token trades or managing open positions.
license: MIT
compatibility: Python 3.11+, Deep Agents
metadata:
  author: Solana Meme Agent Team
  version: "0.1.0"
  hackathon: "Solana Agent Economy Hackathon 2026"
---

# Trade Executor Skill

## Overview

This skill provides trade execution capabilities for Solana DEXs including Raydium, Jupiter, and Orca. It handles swap execution, limit orders, position management, and real-time P&L tracking with built-in risk controls.

## When to Activate

- Executing token swaps based on signals from meme-scanner-skill
- Managing open positions with stop-loss/take-profit
- Performing arb trades between DEXs
- Rebalancing portfolio allocations
- Emergency position exit (panic sell)

## Workflow

### 1. Price Discovery & Slippage

```bash
# Get best quote across DEXs
python scripts/get_quote.py --input <MINT> --output <MINT> --amount <AMOUNT>

# Check price impact
python scripts/check_slippage.py --mint <TOKEN_MINT> --amount <SOL_AMOUNT>

# Monitor price in real-time
python scripts/price_monitor.py --mint <TOKEN_MINT> --interval 5
```

### 2. Trade Execution

```bash
# Execute swap via Jupiter (best route)
python scripts/swap.py --wallet <WALLET> --input <MINT> --output <MINT> --amount <AMOUNT> --slippage 1

# Execute swap via specific DEX
python scripts/swap.py --wallet <WALLET> --input <MINT> --output <MINT> --amount <AMOUNT> --dex raydium

# Limit order (via OpenBook)
python scripts/limit_order.py --wallet <WALLET> --mint <TOKEN_MINT> --side buy --price <PRICE> --amount <AMOUNT>
```

### 3. Position Management

```bash
# Track open positions
python scripts/positions.py --wallet <WALLET>

# Set stop-loss
python scripts/set_stoploss.py --position <MINT> --stop_price <PRICE>

# Set take-profit
python scripts/set_takeprofit.py --position <MINT> --target_price <PRICE>

# Close position
python scripts/close_position.py --wallet <WALLET> --mint <TOKEN_MINT> --percent 100
```

### 4. P&L Tracking

```bash
# Calculate unrealized P&L
python scripts/pnl.py --wallet <WALLET> --unrealized

# Calculate realized P&L (today)
python scripts/pnl.py --wallet <WALLET> --realized --period today

# Export trade history
python scripts/trade_history.py --wallet <WALLET> --output trades.csv
```

## Tool Mapping

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `get_quote.py` | Best route quote | Input/output mints, amount | Quote with price impact |
| `check_slippage.py` | Slippage estimation | Token mint, amount | Slippage percentage |
| `price_monitor.py` | Real-time price feed | Token mint | Price stream |
| `swap.py` | Execute token swap | Wallet, mints, amount, slippage | Transaction signature |
| `limit_order.py` | Place limit order | Wallet, mint, side, price, amount | Order ID |
| `positions.py` | Open positions list | Wallet name | Position list with entry price |
| `set_stoploss.py` | Set stop-loss trigger | Position mint, stop price | Stop-loss ID |
| `set_takeprofit.py` | Set take-profit trigger | Position mint, target price | Take-profit ID |
| `close_position.py` | Exit position | Wallet, mint, percent | Signature, P&L |
| `pnl.py` | P&L calculation | Wallet, period | P&L report |
| `trade_history.py` | Trade log export | Wallet, date range | CSV export |

## Execution Parameters

### Slippage Settings
| Token Type | Recommended Slippage |
|------------|---------------------|
| Major pairs (SOL/USDC) | 0.5% |
| Established alt | 1-2% |
| New meme tokens | 5-10% |
| Low liquidity | 10-15% (avoid) |

### Position Sizing
| Risk Level | Max Position | Stop-Loss |
|------------|-------------|-----------|
| Low (bluechip) | 50 SOL | -20% |
| Medium (alt) | 10 SOL | -30% |
| High (meme) | 2 SOL | -50% |
| Degen (new) | 0.5 SOL | -60% |

## Output Format

### Quote Response
```json
{
  "input_mint": "So11...SOL",
  "output_mint": "EPjF...USDC",
  "input_amount": 10.0,
  "output_amount": 1847.32,
  "price_impact": 0.12,
  "route": ["raydium", "orca"],
  "route_path": "SOL -> USDC (via Raydium)",
  "estimated_slippage": 0.5
}
```

### Swap Execution
```json
{
  "signature": "5j7s...NcXD",
  "type": "swap",
  "input": {"mint": "So11...SOL", "amount": 5.0},
  "output": {"mint": "7xKX...MEME", "amount": 125000.0},
  "price": 0.00004,
  "slippage_used": 0.8,
  "fee_sol": 0.00025,
  "status": "confirmed",
  "timestamp": "2026-01-15T14:22:00Z"
}
```

### Position Report
```json
{
  "wallet": "trading-wallet-1",
  "positions": [
    {
      "mint": "7xKX...MEME",
      "symbol": "MEME",
      "amount": 125000.0,
      "entry_price": 0.00004,
      "current_price": 0.000052,
      "entry_value_sol": 5.0,
      "current_value_sol": 6.5,
      "unrealized_pnl": 1.5,
      "pnl_percent": 30.0,
      "stop_loss": 0.00002,
      "take_profit": 0.00008
    }
  ],
  "total_unrealized_pnl_sol": 1.5,
  "total_portfolio_value_sol": 52.3
}
```

## Safety Rules

### DO
- Always simulate transaction before signing
- Set stop-loss immediately after entry
- Verify token authority status before large buys
- Use Jupiter aggregator for best routes
- Keep 10% of portfolio in SOL for gas
- Test with 10% position before full entry

### DO NOT
- Never trade with more than 20% of portfolio in single position
- Never use more than 10% slippage (likely scam)
- Never trade tokens with <100 SOL liquidity
- Never chase pumps >50% in last hour
- Never disable transaction simulation
- Never trade without checking unlock schedule

## Risk Controls

### Pre-Trade Checks
```python
REQUIRED_CHECKS = [
    "liquidity_locked",
    "mint_authority_revoked",
    "freeze_authority_revoked",
    "holder_count > 100",
    "not_blacklisted"
]

OPTIONAL_CHECKS = [
    "social_score > 50",
    "creator_not_doxxed",
    "audit_completed"
]
```

### Circuit Breakers
```yaml
circuit_breakers:
  max_loss_per_trade: -1.0 SOL      # Auto-sell at -50%
  max_loss_per_day: -5.0 SOL       # Stop trading after -5 SOL
  max_trades_per_hour: 10          # Rate limit
  cooldown_after_loss: 300         # 5 min cooldown after -0.5 SOL trade
```

## Configuration

```yaml
wallets:
  trading: "trading-wallet-1"
  treasury: "treasury-main"

dex_settings:
  preferred_dex: jupiter
  fallback_dexes: [raydium, orca, meteora]
  max_price_impact: 2.0

risk_settings:
  max_position_percent: 20
  max_slippage: 10
  auto_stoploss_percent: 50
  auto_takeprofit_percent: 100

notifications:
  discord_webhook: "<WEBHOOK_URL>"
  notify_on_trade: true
  notify_on_stoploss: true
```

## Testing

```bash
# Run unit tests
cd tests && pytest test_trade_executor.py

# Test on devnet with fake tokens
python scripts/swap.py --wallet test-wallet --input <DEVNET_SOL> --output <DEVNET_TOKEN> --amount 0.1 --network devnet

# Dry-run mode (simulate without executing)
python scripts/swap.py --wallet <WALLET> --input <MINT> --output <MINT> --amount 1 --dry-run
```
