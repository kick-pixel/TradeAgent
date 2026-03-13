# Trade Executor Skill

Execute and manage token trades on Solana DEXs.

## Quick Start

```bash
# Get swap quote
python scripts/get_quote.py --input SOL --output USDC --amount 10

# Execute swap
python scripts/swap.py --wallet my-wallet --input <SOL_MINT> --output <TOKEN_MINT> --amount 1 --slippage 1

# Check positions
python scripts/positions.py --wallet my-wallet
```

## Documentation

See [SKILL.md](./SKILL.md) for full workflow documentation.

## Scripts

| Script | Description |
|--------|-------------|
| `get_quote.py` | Best route quote |
| `check_slippage.py` | Slippage estimation |
| `price_monitor.py` | Real-time price feed |
| `swap.py` | Execute token swap |
| `limit_order.py` | Place limit order |
| `positions.py` | Open positions list |
| `set_stoploss.py` | Set stop-loss trigger |
| `set_takeprofit.py` | Set take-profit trigger |
| `close_position.py` | Exit position |
| `pnl.py` | P&L calculation |
| `trade_history.py` | Trade log export |

## License

MIT
