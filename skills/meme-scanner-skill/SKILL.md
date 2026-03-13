---
name: meme-scanner-skill
description: Discover and analyze new meme tokens on Solana by scanning DEX listings, social media trends, and on-chain metrics. Use when identifying early-stage token opportunities or monitoring meme coin launches.
license: MIT
compatibility: Python 3.11+, Deep Agents
metadata:
  author: Solana Meme Agent Team
  version: "0.1.0"
  hackathon: "Solana Agent Economy Hackathon 2026"
---

# Meme Scanner Skill

## Overview

This skill provides meme token discovery and analysis capabilities by monitoring DEX new listings, tracking social sentiment, and analyzing on-chain launch patterns. It helps identify potential 100x meme coins while filtering out scams.

## When to Activate

- Scanning for new token launches on Raydium, Orca, Meteora
- Monitoring Twitter/Telegram for trending meme tokens
- Analyzing token launch patterns for entry timing
- Tracking whale wallet acquisitions of new tokens
- Building watchlist of potential moonshot candidates

## Workflow

### 1. New Launch Discovery

```bash
# Scan new Raydium listings (last 24h)
python scripts/scan_new_listings.py --dex raydium --hours 24

# Real-time launch monitor
python scripts/launch_monitor.py --min-liquidity 1000 --output alerts.json

# Filter by criteria
python scripts/scan_new_listings.py --min-liquidity 5000 --max-age-hours 12 --output candidates.json
```

### 2. Social Sentiment Analysis

```bash
# Track Twitter mentions
python scripts/track_twitter.py --token <SYMBOL_OR_MINT> --hours 24

# Analyze Telegram sentiment
python scripts/analyze_telegram.py --group <GROUP_URL> --hours 12

# Combined social score
python scripts/social_score.py --token <MINT> --platforms twitter,telegram,discord
```

### 3. On-Chain Analysis

```bash
# Analyze holder distribution
python scripts/analyze_holders.py --mint <TOKEN_MINT>

# Track creator wallet activity
python scripts/track_creator.py --mint <TOKEN_MINT>

# Detect bundled launches
python scripts/detect_bundles.py --mint <TOKEN_MINT> --lookback-hours 6
```

### 4. Token Scoring & Ranking

```bash
# Score single token
python scripts/score_meme.py --mint <TOKEN_MINT>

# Rank all new launches
python scripts/rank_launches.py --min-score 50 --limit 20

# Generate daily report
python scripts/daily_report.py --date today --output report.md
```

## Tool Mapping

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `scan_new_listings.py` | DEX new listing scanner | Dex name, time range, filters | Token list with metadata |
| `launch_monitor.py` | Real-time launch watch | Liquidity threshold | Alert stream |
| `track_twitter.py` | Twitter mention tracker | Token symbol/mint | Mention count, sentiment |
| `analyze_telegram.py` | Telegram sentiment | Group URL | Sentiment score |
| `social_score.py` | Combined social metrics | Token mint | Composite score |
| `analyze_holders.py` | Holder distribution | Token mint | Distribution analysis |
| `track_creator.py` | Creator wallet tracking | Token mint | Creator activity report |
| `detect_bundles.py` | Bundle/bot detection | Token mint | Bundle analysis |
| `score_meme.py` | Full meme token score | Token mint | Score 0-100 with breakdown |
| `rank_launches.py` | Launch ranking | Score threshold | Ranked list |
| `daily_report.py` | Daily opportunity report | Date | Markdown report |

## Scoring Criteria

### Launch Quality (40 points)
- **Liquidity locked**: Yes = +15, No = 0
- **LP amount**: >100 SOL = +10, 50-100 = +5, <50 = 0
- **Creator history**: Clean = +10, Previous rugs = -20
- **Mint/freeze revoked**: Both = +15, One = +5, Neither = 0

### Distribution Quality (25 points)
- **Top 10 holders**: <30% = +15, 30-50% = +5, >50% = 0
- **Bundled launches detected**: No = +10, Yes = -15

### Social Momentum (25 points)
- **Twitter mentions (24h)**: >500 = +10, 100-500 = +5
- **Telegram members**: >1000 = +10, 500-1000 = +5, <100 = 0
- **Sentiment**: Positive = +5, Neutral = 0, Negative = -10

### Token Appeal (10 points)
- **Meme quality**: Viral potential = +10, Generic = +5, Copycat = 0
- **Website/presence**: Professional = +5, Basic = +2, None = 0

## Output Format

### Token Score
```json
{
  "mint": "7xKX...example",
  "symbol": "MEME",
  "name": "Super Meme Coin",
  "score": 78,
  "grade": "A",
  "breakdown": {
    "launch_quality": 35,
    "distribution": 22,
    "social_momentum": 18,
    "token_appeal": 3
  },
  "flags": ["liquidity_locked", "mint_revoked"],
  "warnings": [],
  "recommendation": "BUY - Strong candidate"
}
```

### New Listing Alert
```json
{
  "alert_type": "new_listing",
  "mint": "7xKX...example",
  "symbol": "MOON",
  "dex": "raydium",
  "listed_at": "2026-01-15T14:22:00Z",
  "initial_liquidity_sol": 125.5,
  "price_usd": 0.000234,
  "social_links": {
    "twitter": "https://twitter.com/mooncoin",
    "telegram": "https://t.me/mooncoin"
  },
  "quick_score": 65
}
```

## Safety Rules

### DO
- Always verify liquidity is locked before considering purchase
- Check creator wallet history for previous rug pulls
- Wait minimum 30 minutes after launch for initial volatility
- Cross-reference social links with DexScreener/GeckoTerminal
- Set stop-loss at -50% for meme trades

### DO NOT
- Never buy tokens with mint authority still enabled
- Never chase tokens that already did 10x+ from launch
- Never invest more than 2 SOL in single meme play
- Never trust anonymous team without liquidity lock
- Skip tokens with bundled launches (>20% supply to bots)

## Configuration

```yaml
dexes:
  raydium:
    rpc: "<RPC_URL>"
    api: "https://api.raydium.io"
  orca:
    rpc: "<RPC_URL>"

social_apis:
  twitter:
    bearer_token: "<TWITTER_BEARER>"
  telegram:
    api_id: "<TELEGRAM_API_ID>"
    api_hash: "<TELEGRAM_HASH>"

scoring:
  min_buy_score: 60
  max_position_sol: 2
  required_flags: ["liquidity_locked"]
  auto_reject_flags: ["creator_rug_history", "bundled_launch"]
```

## Testing

```bash
# Run unit tests
cd tests && pytest test_meme_scanner.py

# Test scan with historical data
python scripts/scan_new_listings.py --hours 1 --testnet
```
