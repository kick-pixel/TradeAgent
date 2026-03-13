# Risk Scoring Rules

Comprehensive documentation of the risk scoring formulas, thresholds, and calculation methods used by the Risk Scorer Skill.

## Table of Contents

- [Overview](#overview)
- [Security Score](#security-score)
- [Liquidity Score](#liquidity-score)
- [Transaction Score](#transaction-score)
- [Risk Flag Detection](#risk-flag-detection)
- [Composite Risk Calculation](#composite-risk-calculation)
- [Threshold Explanations](#threshold-explanations)

---

## Overview

The risk scoring system evaluates tokens across **four primary dimensions**:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Security | 35% | Contract authority risks and rug-pull indicators |
| Liquidity | 30% | Pool health, LP locks, holder distribution |
| Transaction | 20% | Trading volume, buyer/seller patterns |
| Holder Analysis | 15% | Concentration risk, whale behavior |

**Final Risk Score** = (Security × 0.35) + (Liquidity × 0.30) + (Transaction × 0.20) + (Holder × 0.15)

Scores range from **0 (lowest risk)** to **100 (critical risk)**.

---

## Security Score

Evaluates smart contract risks using RugCheck API data. Maximum score: **100** (highest risk).

### Scoring Formula

```
Security Score = Σ(factor_weight × factor_score)
```

### RugCheck API Fields Breakdown

| Field | Weight | Risk Contribution | Description |
|-------|--------|-------------------|-------------|
| `mint_authority` | 25% | 0-25 points | `true` = +25, `false` = 0 |
| `freeze_authority` | 20% | 0-20 points | `true` = +20, `false` = 0 |
| `top_10_holder_pct` | 15% | 0-15 points | See holder distribution table below |
| `lp_lock_status` | 20% | 0-20 points | See LP lock table below |
| `contract_verified` | 10% | 0-10 points | `false` = +10, `true` = 0 |
| `blacklist_function` | 10% | 0-10 points | Present = +10, absent = 0 |

### Holder Distribution Scoring

| Top 10 Holder % | Risk Points | Risk Level |
|-----------------|-------------|------------|
| 0-20% | 0 | Low |
| 21-35% | 5 | Low-Medium |
| 36-50% | 10 | Medium |
| 51-65% | 12.5 | Medium-High |
| 66-80% | 15 | High |
| 81-100% | 15 | Critical |

### LP Lock Status Scoring

| LP Status | Risk Points | Description |
|-----------|-------------|-------------|
| Locked >1 year | 0 | Excellent |
| Locked 6-12 months | 5 | Good |
| Locked 1-6 months | 10 | Fair |
| Locked <1 month | 15 | Poor |
| Unlocked | 20 | Critical |
| No LP data | 20 | Unknown/Critical |

### Example Calculation

```json
{
  "mint_authority": true,
  "freeze_authority": true,
  "top_10_holder_pct": 55,
  "lp_lock_status": "unlocked",
  "contract_verified": false,
  "blacklist_function": true
}
```

**Security Score Calculation:**
- Mint Authority: 25 pts (enabled)
- Freeze Authority: 20 pts (enabled)
- Top 10 Holders: 12.5 pts (51-65% range)
- LP Lock: 20 pts (unlocked)
- Contract Verified: 10 pts (not verified)
- Blacklist: 10 pts (present)

**Total: 97.5 / 100** → CRITICAL SECURITY RISK

---

## Liquidity Score

Evaluates pool health and liquidity sustainability. Maximum score: **100** (highest risk).

### Scoring Formula

```
Liquidity Score = (LP_Risk × 0.40) + (Pool_Size_Risk × 0.30) + (Holder_Risk × 0.30)
```

### Component Breakdown

#### 1. LP Percentage Risk (40% weight)

Percentage of total supply in liquidity pool.

| LP % of Supply | Risk Points | Assessment |
|----------------|-------------|------------|
| >80% | 0 | Excellent - well distributed |
| 60-80% | 10 | Good |
| 40-59% | 20 | Fair |
| 20-39% | 30 | Poor |
| 10-19% | 40 | Very Poor |
| <10% | 50 | Critical - potential rug |

#### 2. Pool Size Risk (30% weight)

Based on USD value of liquidity pool.

| Pool Size (USD) | Risk Points | Assessment |
|-----------------|-------------|------------|
| >$500,000 | 0 | Excellent |
| $100,000-$500,000 | 10 | Good |
| $50,000-$100,000 | 20 | Fair |
| $10,000-$50,000 | 30 | Poor |
| $1,000-$10,000 | 40 | Very Poor |
| <$1,000 | 50 | Critical - easily manipulated |

#### 3. Holder Count Risk (30% weight)

Number of unique token holders.

| Holder Count | Risk Points | Assessment |
|--------------|-------------|------------|
| >10,000 | 0 | Excellent |
| 5,000-10,000 | 10 | Good |
| 1,000-5,000 | 20 | Fair |
| 500-1,000 | 30 | Poor |
| 100-500 | 40 | Very Poor |
| <100 | 50 | Critical - low adoption |

### Example Calculation

```
LP % = 35%           → 30 pts × 0.40 = 12.0
Pool Size = $25,000  → 30 pts × 0.30 = 9.0
Holders = 450        → 40 pts × 0.30 = 12.0

Liquidity Score = 12.0 + 9.0 + 12.0 = 33.0 / 100
```

---

## Transaction Score

Evaluates trading patterns and market activity. Maximum score: **100** (highest risk).

### Scoring Formula

```
Transaction Score = (Volume_Risk × 0.35) + (Buy_Sell_Ratio_Risk × 0.35) + (Age_Risk × 0.30)
```

### 24h Volume Risk (35% weight)

| 24h Volume (USD) | Risk Points | Assessment |
|------------------|-------------|------------|
| >$1,000,000 | 0 | Excellent - healthy trading |
| $500,000-$1,000,000 | 10 | Good |
| $100,000-$500,000 | 20 | Fair |
| $50,000-$100,000 | 30 | Poor |
| $10,000-$50,000 | 40 | Very Poor |
| <$10,000 | 50 | Critical - illiquid/manipulated |

### Buyer/Seller Ratio Risk (35% weight)

Ratio of unique buyers to unique sellers in 24h.

| Buyer:Seller Ratio | Risk Points | Assessment |
|--------------------|-------------|------------|
| 0.8-1.2 | 0 | Balanced - healthy |
| 0.6-0.79 or 1.21-1.5 | 15 | Slightly imbalanced |
| 0.4-0.59 or 1.51-2.0 | 30 | Imbalanced - caution |
| 0.2-0.39 or 2.01-3.0 | 40 | Highly imbalanced |
| <0.2 or >3.0 | 50 | Critical - manipulation likely |

**Red Flags:**
- Ratio >3.0: Possible coordinated buying/pump
- Ratio <0.2: Mass exit/panic selling

### Token Age Risk (30% weight)

| Token Age | Risk Points | Assessment |
|-----------|-------------|------------|
| >1 year | 0 | Established |
| 6-12 months | 10 | Maturing |
| 1-6 months | 20 | Fair |
| 1-4 weeks | 30 | New - higher risk |
| 1-7 days | 40 | Very new |
| <24 hours | 50 | Critical - sniper territory |

### Example Calculation

```
24h Volume = $75,000     → 30 pts × 0.35 = 10.5
Buy/Sell Ratio = 2.5     → 40 pts × 0.35 = 14.0
Token Age = 3 days       → 40 pts × 0.30 = 12.0

Transaction Score = 10.5 + 14.0 + 12.0 = 36.5 / 100
```

---

## Risk Flag Detection

Automatic flags triggered by specific conditions. These are **binary indicators** that add to the overall risk assessment.

### Critical Flags (Auto-Fail)

| Flag | Condition | Action |
|------|-----------|--------|
| `MINT_ENABLED` | Mint authority = true | Immediate HIGH risk |
| `FREEZE_ENABLED` | Freeze authority = true | Immediate HIGH risk |
| `BLACKLIST_DETECTED` | Blacklist function in contract | Immediate HIGH risk |
| `HONEYPOT_DETECTED` | Buys allowed, sells blocked | CRITICAL - avoid |
| `LP_UNLOCKED` | No LP lock or unlocked | HIGH risk |

### Warning Flags

| Flag | Condition | Risk Addition |
|------|-----------|---------------|
| `NEW_TOKEN` | Age < 7 days | +15 points |
| `LOW_LIQUIDITY` | Pool < $10,000 | +20 points |
| `CONCENTRATED_HOLDERS` | Top 10 > 60% | +15 points |
| `LOW_VOLUME` | 24h vol < $10,000 | +10 points |
| `UNVERIFIEDContract` | Source not verified | +10 points |
| `SUSPICIOUS_RATIO` | Buy/sell > 2.5 or < 0.4 | +15 points |

### Informational Flags

| Flag | Condition | Notes |
|------|-----------|-------|
| `HIGH_VELOCITY` | Volume/MCAP > 100% | High trading activity |
| `WHALE_ACCUMULATION` | Large buyer detected | Monitor for pump/dump |
| `DEV_HOLDING` | Dev wallet > 5% | Track for dumps |
| `BUNDLED_LAUNCH` | Multiple buys at launch | Possible insider activity |

---

## Composite Risk Calculation

### Final Score Formula

```
Risk Score = (Security × 0.35) + (Liquidity × 0.30) + (Transaction × 0.20) + (Holder × 0.15)
```

### Flag Modifiers

Flags adjust the final score:

```
Adjusted Score = Base Score + Σ(flag_modifiers)
```

| Flag Type | Modifier |
|-----------|----------|
| Critical Flag | +25 points |
| Warning Flag | +10 points each |
| Informational | +0 points (tracking only) |

**Maximum capped at 100.**

### Risk Level Classification

| Final Score | Risk Level | Color | Recommended Action |
|-------------|------------|-------|-------------------|
| 0-20 | LOW | 🟢 Green | Safe to trade |
| 21-40 | MEDIUM | 🟡 Yellow | Proceed with caution |
| 41-60 | ELEVATED | 🟠 Orange | Reduce position size |
| 61-80 | HIGH | 🔴 Red | Avoid unless verified |
| 81-100 | CRITICAL | ⚫ Black | DO NOT TRADE |

---

## Threshold Explanations

### Why These Thresholds?

#### Security Thresholds

- **Mint Authority (25%)**: Highest weight because enabled mint = infinite supply risk
- **Freeze Authority (20%)**: Can freeze all holder assets instantly
- **LP Lock (20%)**: Unlocked LP = liquidity can be removed anytime
- **Top Holders (15%)**: Concentration enables price manipulation
- **Verification (10%)**: Unverified = hidden malicious code possible
- **Blacklist (10%)**: Can prevent specific addresses from selling

#### Liquidity Thresholds

- **LP % (40%)**: Low LP % = devs holding supply to dump
- **Pool Size (30%)**: Small pools = easy manipulation, high slippage
- **Holders (30%)**: Few holders = low adoption, exit scam risk

#### Transaction Thresholds

- **Volume (35%)**: Low volume = illiquid, hard to exit
- **Buy/Sell Ratio (35%)**: Imbalance = manipulation or panic
- **Age (30%)**: New tokens = unproven, higher rug risk

### Risk Tolerance Settings

Users can configure thresholds based on risk appetite:

```yaml
# Conservative (safe-first)
conservative:
  low: 15
  medium: 30
  elevated: 45
  high: 60

# Balanced (default)
balanced:
  low: 20
  medium: 40
  elevated: 60
  high: 80

# Aggressive (higher risk tolerance)
aggressive:
  low: 25
  medium: 50
  elevated: 65
  high: 85
```

---

## Quick Reference

### Red Flags Checklist

Before any trade, verify:

- [ ] Mint authority = **false** (revoked)
- [ ] Freeze authority = **false** (revoked)
- [ ] LP locked > 6 months
- [ ] Top 10 holders < 50%
- [ ] Pool size > $50,000
- [ ] Token age > 7 days
- [ ] 24h volume > $50,000
- [ ] Buy/sell ratio 0.5-2.0

### Instant Rejection Criteria

Reject token immediately if **ANY** of the following:

1. Mint authority enabled
2. Freeze authority enabled
3. Blacklist function detected
4. Honeypot detected
5. LP unlocked + top holder > 50%
6. Risk score > 80 (CRITICAL)
