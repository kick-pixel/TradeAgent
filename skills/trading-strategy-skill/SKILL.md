---
name: trading-strategy
version: "2026.3.13-1"
updated: "2026-03-13"
description: "Provide trading strategy guidance and risk management rules for Solana meme coin trading. Use when the user asks about position sizing, entry/exit strategies, portfolio management, or risk controls. Helps the agent make informed trading decisions."
---

# Trading Strategy Skill

## Purpose

Provide trading strategy guidance and risk management framework for Solana meme coin trading. This skill provides strategic recommendations - the AI agent and user make the final trading decisions.

## When to Use

Use this skill when:
- User asks about position sizing
- User wants entry/exit strategy advice
- User needs portfolio risk management guidance
- Agent is evaluating a trade opportunity
- User asks about stop-loss or take-profit levels

## Core Principles

### 1. Capital Preservation First
- Never risk more than you can afford to lose
- Protect the portfolio from catastrophic losses
- Live to trade another day

### 2. Position Sizing
- Never go "all in" on a single token
- Diversify across multiple positions
- Size based on risk score and conviction

### 3. Risk/Reward Balance
- Only take trades with favorable risk/reward
- Cut losses quickly, let profits run
- Pre-define exit points before entry

## Position Sizing Framework

### By Risk Score

| Risk Score | Max Position Size | Notes |
|------------|-------------------|-------|
| 80-100 | 5% of portfolio | Low risk, normal sizing |
| 60-79 | 3% of portfolio | Medium risk, reduced size |
| 40-59 | 1-2% of portfolio | High risk, minimal exposure |
| 0-39 | 0% | Do not trade |

### By Conviction Level

| Conviction | Position Adjustment |
|------------|---------------------|
| High (multiple bullish signals) | 1.5x base size |
| Medium (mixed signals) | 1x base size |
| Low (speculative) | 0.5x base size |

### Example Calculation

```
Portfolio Value: $1,000
Token Risk Score: 75 (Medium Risk)
Base Position: 3%
Conviction: High (1.5x)

Position Size = $1,000 × 3% × 1.5 = $45
```

## Entry Strategy

### Pre-Entry Checklist

Before any trade, verify:

- [ ] Security audit passed (risk score ≥ 50)
- [ ] Sufficient liquidity (≥ $10,000)
- [ ] Recent trading activity (volume > $5k/24h)
- [ ] Price trend favorable (not in free fall)
- [ ] Risk rules passed (daily limit, max holdings)
- [ ] User has confirmed the trade

### Entry Timing

**Good Entry Signals:**
- Price consolidating after initial pump
- Volume increasing while price stable
- Multiple timeframe alignment (1h and 4h both bullish)
- RSI oversold or neutral

**Avoid Entry When:**
- Price already up 50%+ in 24h
- Volume declining while price rising
- Clear downtrend on higher timeframes
- RSI extremely overbought (> 80)

## Exit Strategy

### Stop Loss Rules

| Scenario | Stop Loss Level |
|----------|-----------------|
| Default | -15% from entry |
| High volatility token | -20% from entry |
| Low liquidity token | -25% from entry |
| After significant gain (trail) | -10% from peak |

### Take Profit Rules

| Scenario | Take Profit Level |
|----------|-------------------|
| Conservative | +30% from entry |
| Moderate | +50% from entry |
| Aggressive | +100% from entry |

### Partial Exit Strategy

Consider taking partial profits at each level:

```
Example: $100 position
- At +30%: Sell 25% ($25) → Lock $7.50 profit
- At +50%: Sell 25% ($25) → Lock $12.50 profit  
- At +100%: Sell 25% ($25) → Lock $25 profit
- Remainder: Trail with -10% stop
```

### Time-Based Exit

If position has been held for extended period:

| Hold Time | Action |
|-----------|--------|
| < 4 hours | Hold (normal) |
| 4-12 hours | Monitor closely |
| 12-24 hours | Consider exit if profit < 5% |
| > 24 hours | Exit if not at profit target |

## Portfolio Risk Management

### Maximum Exposure Limits

| Metric | Limit |
|--------|-------|
| Single position | 5% of portfolio |
| Total meme positions | 15% of portfolio |
| Daily trade count | 5 trades |
| Concurrent holdings | 3 tokens |
| Daily loss limit | 10% of portfolio |

### Correlation Risk

- Avoid holding multiple tokens in same narrative
- Diversify across different meme themes
- Don't double down on losing positions

## Strategy Templates

### 1. Momentum Strategy

For tokens with strong upward momentum:

```
Entry:
- Risk score ≥ 60
- 24h volume up 100%+
- Price up 10-30% in 24h

Position: 3-5% of portfolio

Exit:
- Stop loss: -15%
- Take profit 1: +30% (sell 25%)
- Take profit 2: +50% (sell 25%)
- Trail remainder with -10% stop
```

### 2. Dip Buy Strategy

For quality tokens in temporary pullback:

```
Entry:
- Risk score ≥ 70
- Price down 15-30% from recent high
- Volume declining (panic selling exhausted)

Position: 2-3% of portfolio

Exit:
- Stop loss: -20%
- Take profit: +20% (previous resistance)
```

### 3. New Launch Strategy

For newly launched meme coins:

```
Entry:
- Risk score ≥ 50 (if available)
- Launch < 24 hours
- Initial liquidity > $10,000
- Holder count growing

Position: 1-2% of portfolio (highly speculative)

Exit:
- Stop loss: -25%
- Take profit: +50% (quick scalp)
- Maximum hold: 4 hours
```

## Decision Framework

When evaluating a trade opportunity:

### Step 1: Risk Assessment
1. Get token security data
2. Calculate risk score
3. If score < 50 → STOP, do not trade

### Step 2: Market Analysis
1. Check price trend (K-line)
2. Analyze volume and activity
3. Assess market sentiment

### Step 3: Position Planning
1. Determine base position size from risk score
2. Adjust for conviction level
3. Set stop loss and take profit levels

### Step 4: Risk Check
1. Verify against risk rules
2. Check daily limits
3. Confirm portfolio exposure OK

### Step 5: Execution
1. Present full analysis to user
2. Get explicit confirmation
3. Execute trade
4. Record position for tracking

## Example Analysis Output

```
Token: [SYMBOL]
Contract: [ADDRESS]

Risk Assessment:
- Risk Score: 72/100 (Medium Risk)
- Not a honeypot ✓
- Taxes: Buy 5% / Sell 5% ✓
- Liquidity: $35,000 ✓

Market Analysis:
- 24h Volume: $125,000 (+150%)
- Price Trend: Consolidating after +25% pump
- Holders: 450 (growing)

Position Recommendation:
- Size: 3% of portfolio = $30 (on $1,000 portfolio)
- Entry: Current price or slight dip
- Stop Loss: -15%
- Take Profit: +30% (sell half), +50% (trail)

Risk/Reward: 1:2 (favorable)

⚠️ Note: Medium risk token - reduce position if uncertain
```

## Important Notes

1. **Guidance, not commands** - These are recommendations; agent/user decide
2. **Adapt to conditions** - Market conditions may require strategy adjustments
3. **Past ≠ future** - Historical performance doesn't guarantee results
4. **User's capital** - Always respect user's risk tolerance
5. **Learn and improve** - Track outcomes to refine strategy

## Related Skills

- `meme-scanner-skill`: For discovering trading opportunities
- `risk-scorer-skill`: For token security analysis
- `bitget-wallet-skill`: For executing trades
