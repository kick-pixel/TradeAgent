---
name: meme-scanner
version: "2026.3.13-1"
updated: "2026-03-13"
description: "Discover and analyze Solana meme coins. Use when the user asks about trending tokens, new launches, hot picks, or wants to scan for trading opportunities. Provides token discovery, market data analysis, and activity monitoring."
---

# Meme Scanner Skill

## Purpose

Discover and analyze Solana meme coins for potential trading opportunities. This skill provides data and analysis tools - the AI agent makes all trading decisions based on the information provided.

## When to Use

Use this skill when:
- User asks about trending/hot meme tokens
- User wants to discover new token launches
- User wants to analyze market activity for specific tokens
- User asks for trading opportunities or alpha

## Tools Available

### 1. Trending Tokens Discovery

Get currently trending tokens from Bitget Wallet's curated lists.

```bash
python3 ../bitget-wallet-skill/scripts/bitget_agent_api.py rankings --name Hotpicks
python3 ../bitget-wallet-skill/scripts/bitget_agent_api.py rankings --name topGainers
python3 ../bitget-wallet-skill/scripts/bitget_agent_api.py rankings --name topLosers
```

**Response includes:**
- Token symbol, name, contract address
- Current price and 24h change
- Market cap and liquidity info

### 2. New Token Discovery

Find recently launched tokens by timestamp.

```bash
python3 ../bitget-wallet-skill/scripts/bitget_agent_api.py historical-coins --create-time "2026-03-13 00:00:00" --limit 20
```

**Use this to:**
- Find newly launched meme coins
- Detect early opportunities
- Track token launches over time

### 3. Token Transaction Activity

Analyze trading activity for a specific token.

```bash
python3 ../bitget-wallet-skill/scripts/bitget_agent_api.py tx-info --chain sol --contract <TOKEN_ADDRESS>
```

**Response includes:**
- Buy/sell volume (5m, 1h, 4h, 24h)
- Number of unique traders
- Price change percentages

### 4. Token Price & Info

Get current price and detailed info for a token.

```bash
python3 ../bitget-wallet-skill/scripts/bitget_agent_api.py token-info --chain sol --contract <TOKEN_ADDRESS>
python3 ../bitget-wallet-skill/scripts/bitget_agent_api.py token-price --chain sol --contract <TOKEN_ADDRESS>
```

### 5. K-Line (Candlestick) Data

Get historical price data for trend analysis.

```bash
python3 ../bitget-wallet-skill/scripts/bitget_agent_api.py kline --chain sol --contract <TOKEN_ADDRESS> --period 1h --size 24
```

**Periods available:** 1s, 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w

### 6. Token Search

Search for tokens by name, symbol, or contract.

```bash
python3 ../bitget-wallet-skill/scripts/bitget_agent_api.py search-tokens --keyword "PEPE" --chain sol
```

## Analysis Framework

When scanning for meme tokens, analyze:

### 1. Market Momentum
- **Top Gainers**: Tokens with significant price increases
- **Hot Picks**: Curated trending tokens
- **Volume**: High trading volume indicates interest

### 2. Activity Signals
- **Trader Count**: More unique traders = more interest
- **Buy/Sell Ratio**: More buys than sells = bullish
- **Volume Trends**: Increasing volume = momentum

### 3. Price Patterns
- Use K-line data to identify:
  - Uptrends (higher highs)
  - Breakouts (volume + price spike)
  - Consolidation (potential breakout)

## Decision Guidance

**The AI Agent should use this data to make decisions, considering:**

### High-Potential Signals
- Strong 24h volume (> $100k)
- Increasing trader count
- Price uptrend with volume confirmation
- Positive market sentiment

### Warning Signs
- Low liquidity (< $10k)
- Declining trader count
- Price pumping without volume
- Recent launch with no track record

## Example Workflow

```
1. User: "Find me the hottest Solana meme coins right now"

2. Agent actions:
   a. Run: rankings --name Hotpicks
   b. For each token in top 5:
      - Run: tx-info to check activity
      - Run: kline to check price trend
   c. Analyze and rank tokens
   d. Present findings with buy/watch/avoid recommendations

3. Output: Summary of each token with analysis and recommendation
```

## Chain Codes

| Chain | Code |
|-------|------|
| Solana | sol |
| Ethereum | eth |
| BNB Chain | bnb |
| Base | base |
| Arbitrum | arbitrum |

Use empty string `""` for native token contract (SOL, ETH, etc.)

## Important Notes

1. **Data is for analysis only** - This skill provides market data, not trading signals
2. **Agent makes decisions** - The AI agent should interpret data and make recommendations
3. **Always cross-check** - Combine multiple data points before conclusions
4. **Real-time data** - Prices change rapidly; re-check before trading
5. **Risk awareness** - Meme coins are highly volatile; always check security

## Related Skills

- `bitget-wallet-skill`: For executing swaps and managing wallet
- `risk-scorer-skill`: For security audits and risk assessment
- `trading-strategy-skill`: For position sizing and risk management
