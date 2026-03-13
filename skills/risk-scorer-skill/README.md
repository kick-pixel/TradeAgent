# Risk Scorer Skill

Wallet and token risk assessment for Solana trading.

## Quick Start

```bash
# Analyze wallet risk
python scripts/analyze_wallet.py --wallet <ADDRESS>

# Score token risk
python scripts/score_token.py --mint <TOKEN_MINT>
```

## Documentation

See [SKILL.md](./SKILL.md) for full workflow documentation.

## Scripts

| Script | Description |
|--------|-------------|
| `analyze_wallet.py` | Full wallet risk profile |
| `batch_analyze.py` | Multi-wallet screening |
| `score_token.py` | Token contract analysis |
| `check_liquidity.py` | LP lock verification |
| `detect_wash_trading.py` | Volume manipulation detection |
| `detect_sniping.py` | MEV/sniper identification |

## License

MIT
