---
name: wallet-manager-skill
description: Manage multiple Solana wallets including key generation, balance tracking, token transfers, and portfolio allocation. Use when operating multi-wallet strategies or managing treasury funds.
license: MIT
compatibility: Python 3.11+, Deep Agents
metadata:
  author: Solana Meme Agent Team
  version: "0.1.0"
  hackathon: "Solana Agent Economy Hackathon 2026"
---

# Wallet Manager Skill

## Overview

This skill provides comprehensive wallet management capabilities for multi-wallet operations on Solana. It handles key management, balance tracking, token transfers, and portfolio rebalancing across multiple wallets.

## When to Activate

- Managing multiple trading wallets
- Setting up new wallet infrastructure
- Consolidating funds from multiple wallets
- Distributing funds for airdrops or payments
- Tracking portfolio across wallets
- Rotating wallet keys for security

## Workflow

### 1. Wallet Generation & Import

```bash
# Generate new wallet with encrypted keyfile
python scripts/generate_wallet.py --name <WALLET_NAME> --password

# Import existing wallet from private key
python scripts/import_wallet.py --name <WALLET_NAME> --key <PRIVATE_KEY>

# Import from Sollet/Paper wallet
python scripts/import_wallet.py --name <WALLET_NAME> --json <PATH>
```

### 2. Balance & Portfolio Tracking

```bash
# Get SOL balance for wallet
python scripts/get_balance.py --wallet <NAME_OR_ADDRESS>

# Get all token holdings
python scripts/get_tokens.py --wallet <NAME_OR_ADDRESS>

# Full portfolio snapshot
python scripts/portfolio_snapshot.py --wallets all --output <PATH>
```

### 3. Token Transfers

```bash
# Transfer SOL
python scripts/transfer_sol.py --from <WALLET> --to <ADDRESS> --amount <SOL>

# Transfer SPL tokens
python scripts/transfer_token.py --from <WALLET> --to <ADDRESS> --mint <TOKEN_MINT> --amount <AMOUNT>

# Batch transfer (airdrop mode)
python scripts/batch_transfer.py --from <WALLET> --recipients <CSV> --amount <AMOUNT>
```

### 4. Wallet Consolidation

```bash
# Sweep all tokens from wallet to treasury
python scripts/sweep_wallet.py --from <WALLET> --to <TREASURY_WALLET>

# Consolidate multiple wallets
python scripts/consolidate.py --sources <CSV> --destination <TREASURY>
```

## Tool Mapping

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `generate_wallet.py` | Create new wallet | Name, password | Keypair file, address |
| `import_wallet.py` | Import existing wallet | Private key/JSON | Encrypted keyfile |
| `get_balance.py` | SOL balance check | Wallet name/address | SOL amount |
| `get_tokens.py` | Token holdings list | Wallet name/address | Token list with amounts |
| `portfolio_snapshot.py` | Full portfolio report | Wallet list | JSON report |
| `transfer_sol.py` | SOL transfer | From, to, amount | Signature |
| `transfer_token.py` | SPL token transfer | From, to, mint, amount | Signature |
| `batch_transfer.py` | Multi-recipient transfer | From, recipients CSV, amount | Batch signatures |
| `sweep_wallet.py` | Full wallet sweep | Source, destination | Transaction list |
| `consolidate.py` | Multi-wallet consolidation | Sources, destination | Consolidation report |

## Security Features

### Key Storage
- All private keys stored in encrypted JSON keyfiles
- Encryption using Fernet (symmetric) with user password
- Keyfiles stored in `~/.solana/wallets/` directory
- Never log or print private keys

### Transaction Signing
- All transactions signed locally (never send keys to RPC)
- Transaction simulation before signing
- Configurable spending limits per wallet

## Output Format

### Wallet Info
```json
{
  "name": "trading-wallet-1",
  "address": "7xKX...example",
  "created_at": "2026-01-15T10:30:00Z",
  "label": "Main Trading Wallet"
}
```

### Portfolio Snapshot
```json
{
  "wallet": "7xKX...example",
  "sol_balance": 45.234,
  "tokens": [
    {"mint": "EPjF...USD", "symbol": "USDC", "amount": 1000.00, "usd_value": 1000.00},
    {"mint": "Es9v...SOL", "symbol": "SOL", "amount": 10.5, "usd_value": 1890.00}
  ],
  "total_usd_value": 10052.34,
  "snapshot_time": "2026-01-15T14:22:00Z"
}
```

### Transfer Result
```json
{
  "signature": "5j7s...NcXD",
  "from": "7xKX...example",
  "to": "DyKg...example",
  "amount": 5.0,
  "token": "SOL",
  "status": "confirmed",
  "slot": 245892341
}
```

## Safety Rules

### DO
- Always backup keyfiles to secure location immediately after creation
- Test transfers with small amounts before large transactions
- Use hardware wallets for treasury/storage wallets (>100 SOL)
- Rotate wallet keys every 90 days for active trading wallets
- Set spending limits: max 10 SOL per transaction for hot wallets

### DO NOT
- Never commit keyfiles to version control
- Never share private keys or encrypted keyfiles
- Never use same wallet for trading and long-term storage
- Never transfer more than 50% of wallet balance in single transaction
- Never skip transaction simulation step

## Configuration

```yaml
wallets_dir: "~/.solana/wallets"
network: mainnet-beta  # or testnet, devnet
rpc_url: "https://api.mainnet-beta.solana.com"
commitment: confirmed

spending_limits:
  trading:
    max_sol_per_tx: 10
    max_usd_per_tx: 1500
  treasury:
    max_sol_per_tx: 100
    max_usd_per_tx: 15000
    requires_confirmation: true
```

## Wallet Labeling System

```
Naming Convention:
<trype>-<purpose>-<number>

Examples:
- trading-meme-1      # Meme coin trading wallet 1
- trading-swing-1     # Swing trading wallet
- treasury-main       # Main treasury (cold storage)
- treasury-ops        # Operational expenses
- airdrop-sender      # Dedicated airdrop wallet
```

## Testing

```bash
# Run unit tests
cd tests && pytest test_wallet_manager.py

# Test on devnet first
python scripts/generate_wallet.py --name test-wallet --network devnet
python scripts/transfer_sol.py --from test-wallet --to <ADDRESS> --amount 0.1 --network devnet
```
