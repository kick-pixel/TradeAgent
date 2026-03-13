# Wallet Manager Skill

Multi-wallet management for Solana trading operations.

## Quick Start

```bash
# Generate new wallet
python scripts/generate_wallet.py --name my-wallet --password

# Check balance
python scripts/get_balance.py --wallet my-wallet

# Transfer SOL
python scripts/transfer_sol.py --from my-wallet --to <ADDRESS> --amount 1
```

## Documentation

See [SKILL.md](./SKILL.md) for full workflow documentation.

## Scripts

| Script | Description |
|--------|-------------|
| `generate_wallet.py` | Create new wallet |
| `import_wallet.py` | Import existing wallet |
| `get_balance.py` | SOL balance check |
| `get_tokens.py` | Token holdings list |
| `portfolio_snapshot.py` | Full portfolio report |
| `transfer_sol.py` | SOL transfer |
| `transfer_token.py` | SPL token transfer |
| `batch_transfer.py` | Multi-recipient transfer |
| `sweep_wallet.py` | Full wallet sweep |
| `consolidate.py` | Multi-wallet consolidation |

## License

MIT
