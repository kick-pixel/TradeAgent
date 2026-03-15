---
name: risk-scorer
version: "2026.3.13-1"
updated: "2026-03-13"
description: "Assess risk and security of Solana meme tokens. Use when the user asks about token safety, honeypot checks, contract audits, or risk scoring. Provides comprehensive security analysis to help make informed trading decisions."
---

# Risk Scorer Skill

## Purpose

Assess the risk profile of Solana meme tokens through comprehensive security analysis. This skill provides risk data and analysis - the AI agent interprets the results and makes trading decisions.

## When to Use

Use this skill when:
- User asks "Is this token safe?"
- User wants to check for honeypots
- User needs contract security audit
- User asks for risk score before trading
- Analyzing any new token

**IMPORTANT**: Always run risk assessment BEFORE suggesting any buy trade.

## Tools Available

### 1. Security Audit

Comprehensive contract security analysis.

```bash
python3 ../bitget-wallet-skill/scripts/bitget_agent_api.py security --chain sol --contract <TOKEN_ADDRESS>
```

**Response includes:**
- `highRisk`: Boolean - Is this a high-risk token?
- `riskCount`: Number of risk factors detected
- `buyTax`: Buy transaction tax percentage
- `sellTax`: Sell transaction tax percentage
- `isHoneypot`: Boolean - Potential honeypot detection
- `isOpenSource`: Boolean - Is contract source verified?
- `holderCount`: Number of token holders
- Additional security flags and warnings

### 2. Token Risk Check

Pre-swap risk validation (Bitget API specific).

```bash
python3 ../bitget-wallet-skill/scripts/bitget_agent_api.py check-swap-token \
  --from-chain sol --from-contract "" --from-symbol SOL \
  --to-chain sol --to-contract <TOKEN_ADDRESS> --to-symbol <SYMBOL>
```

**Checks for:**
- Forbidden-buy tokens (cannot be purchased)
- Risk warnings specific to trading
- Platform-level risk flags

**Response:**
- `error_code != 0`: API error, check `msg`
- `data.list[].checkTokenList`: Array of risk items
- `waringType`: "forbidden-buy" means token cannot be bought

### 3. Liquidity Check

Assess liquidity depth and available pools.

```bash
python3 ../bitget-wallet-skill/scripts/bitget_agent_api.py liquidity --chain sol --contract <TOKEN_ADDRESS>
```

**Low liquidity risks:**
- High slippage on trades
- Price manipulation vulnerability
- Difficulty exiting positions

### 4. Holder Analysis

Get token holder information from security audit response:
- `holderCount`: Number of unique holders
- Low holder count = concentrated ownership risk

## Risk Scoring Framework

### Score Calculation (0-100, higher = safer)

The AI agent should calculate a risk score based on:

#### Critical Factors (Auto-fail)
| Factor | Condition | Action |
|--------|-----------|--------|
| Honeypot | `isHoneypot = true` | **Score = 0, AVOID** |
| Forbidden-buy | `waringType = "forbidden-buy"` | **Score = 0, AVOID** |
| High Risk | `highRisk = true` | **Score ≤ 20, AVOID** |

#### Tax Analysis
| Tax Rate | Score Impact |
|----------|--------------|
| Buy + Sell ≤ 5% | +20 points |
| Buy + Sell 5-10% | +10 points |
| Buy + Sell 10-20% | +0 points |
| Buy + Sell > 20% | -20 points |
| Buy tax > 10% | -10 points |
| Sell tax > 10% | -15 points (exit difficulty) |

#### Liquidity Analysis
| Liquidity USD | Score Impact |
|---------------|--------------|
| > $100,000 | +20 points |
| $50,000 - $100,000 | +10 points |
| $10,000 - $50,000 | +5 points |
| < $10,000 | -15 points |

#### Holder Analysis
| Holder Count | Score Impact |
|--------------|--------------|
| > 1,000 | +15 points |
| 500 - 1,000 | +10 points |
| 100 - 500 | +5 points |
| < 100 | -10 points |

#### Contract Verification
| Factor | Score Impact |
|--------|--------------|
| Open Source | +10 points |
| Closed Source | -5 points |

### Example Score Calculation

```
Token Analysis:
- Honeypot: false
- High Risk: false
- Buy Tax: 5%
- Sell Tax: 5%
- Liquidity: $150,000
- Holders: 800
- Open Source: true

Base Score: 50
+ Tax (≤10%): +10
+ Liquidity (>$100k): +20
+ Holders (500-1000): +10
+ Open Source: +10
= Final Score: 100

Result: SAFE TO TRADE
```

## Risk Levels

| Score | Risk Level | Recommendation |
|-------|------------|----------------|
| 80-100 | Low Risk | Generally safe to trade |
| 60-79 | Medium Risk | Trade with caution, smaller position |
| 40-59 | High Risk | Avoid or minimal exposure only |
| 0-39 | Very High Risk | **DO NOT TRADE** |

## Red Flags (Immediate Avoid)

1. **Honeypot detected** - Cannot sell after buying
2. **Forbidden-buy** - Blocked by platform
3. **High-risk flag** - Multiple serious issues
4. **Sell tax > 20%** - Very difficult to exit
5. **Liquidity < $5,000** - Easy to manipulate
6. **Holder count < 50** - Concentrated ownership

## Example Workflow

```
1. User: "Should I buy [TOKEN_ADDRESS]?"

2. Agent actions:
   a. Run: security --chain sol --contract <ADDRESS>
   b. Run: liquidity --chain sol --contract <ADDRESS>
   c. Run: check-swap-token for trading validation
   d. Calculate risk score using framework above
   e. Provide recommendation with data

3. Output example:
   "Risk Score: 75/100 (Medium Risk)
   
   ✅ Not a honeypot
   ✅ Verified contract
   ⚠️ Buy tax: 8%, Sell tax: 8%
   ✅ Liquidity: $45,000
   ✅ Holders: 350
   
   Recommendation: TRADE WITH CAUTION
   - Reduce position size to 2-3% of portfolio
   - Set tight stop loss
   - Monitor for unusual activity"
```

## Important Notes

1. **Security first** - Always check security before any buy recommendation
2. **Multiple data points** - Don't rely on single metric
3. **Dynamic assessment** - Risk profiles can change; re-check periodically
4. **False negatives possible** - Some scams pass basic checks
5. **Human judgment** - Final decision always with user

## Related Skills

- `meme-scanner-skill`: For discovering tokens to analyze
- `bitget-wallet-skill`: For executing trades after risk check
- `trading-strategy-skill`: For position sizing based on risk score
