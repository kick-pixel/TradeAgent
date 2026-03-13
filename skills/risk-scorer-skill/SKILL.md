---
name: risk-scorer-skill
description: Evaluate wallet and token risk levels by analyzing on-chain data, transaction history, token holdings, and contract security. Use when assessing counterparty risk before trades, screening new tokens, or detecting suspicious activity.
license: MIT
compatibility: Python 3.11+, Deep Agents
metadata:
  author: Solana Meme Agent Team
  version: "0.2.0"
  hackathon: "Solana Agent Economy Hackathon 2026"
  docs: "./docs/"
---

# Risk Scorer Skill

## Overview

This skill provides comprehensive wallet and token risk assessment capabilities by analyzing:

- **Smart contract security** (mint/freeze authority, LP locks, holder distribution)
- **Transaction patterns** (wash trading, sniper activity, DEX interactions)
- **Portfolio composition** (token concentration, high-risk exposure)
- **Market dynamics** (volume patterns, buyer/seller ratios)

The skill outputs **risk scores (0-100)** with actionable recommendations.

## When to Activate

| Scenario | Trigger Condition | Priority |
|----------|-------------------|----------|
| Pre-trade screening | About to trade with unknown wallet/token | **HIGH** |
| Token due diligence | Evaluating new token for investment | **HIGH** |
| Portfolio audit | Regular risk assessment of holdings | MEDIUM |
| Suspicious activity | Unusual transaction patterns detected | **HIGH** |
| Compliance check | Audit trail generation required | MEDIUM |
| Post-trade analysis | Review completed trade counterparty | LOW |

### Activation Phrases

```
- "Analyze the risk of wallet <ADDRESS>"
- "Score token <MINT> for rug-pull risk"
- "Check if <WALLET> is safe to trade with"
- "Run risk assessment on my portfolio"
- "Detect wash trading in <WALLET>"
- "Is <TOKEN> a honeypot?"
```

---

## Complete Workflow

### Step 1: Input Validation

Before running any analysis, validate inputs:

```python
from scripts.validators import validate_wallet_address, validate_token_mint

# Validate wallet address (Solana base58)
wallet = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
if not validate_wallet_address(wallet):
    raise ValueError("Invalid wallet address format")

# Validate token mint
mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
if not validate_token_mint(mint):
    raise ValueError("Invalid token mint format")
```

### Step 2: Data Collection

Gather data from multiple sources in parallel:

```python
import asyncio
from scripts.rugcheck_client import RugCheckClient
from scripts.bitget_client import BitgetClient

async def collect_token_data(mint: str) -> dict:
    """Collect all data for token risk scoring."""
    rugcheck = RugCheckClient()
    bitget = BitgetClient()
    
    # Parallel API calls
    tasks = [
        rugcheck.get_token_report(mint),
        rugcheck.get_pool_report(mint),
        bitget.get_token_holdings(mint),
        bitget.get_transaction_history(mint, hours=24)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        "security_report": results[0] if not isinstance(results[0], Exception) else None,
        "pool_report": results[1] if not isinstance(results[1], Exception) else None,
        "holdings": results[2] if not isinstance(results[2], Exception) else None,
        "transactions": results[3] if not isinstance(results[3], Exception) else None
    }
```

### Step 3: Score Calculation

Apply weighted scoring formula:

```python
from scripts.scorers import SecurityScorer, LiquidityScorer, TransactionScorer

def calculate_risk_score(data: dict) -> dict:
    """Calculate composite risk score."""
    
    # Calculate individual dimension scores
    security_score = SecurityScorer.score(data["security_report"])
    liquidity_score = LiquidityScorer.score(data["pool_report"], data["holdings"])
    transaction_score = TransactionScorer.score(data["transactions"])
    
    # Composite score (weighted average)
    composite = (
        security_score * 0.35 +
        liquidity_score * 0.30 +
        transaction_score * 0.20 +
        holder_score * 0.15
    )
    
    # Determine risk level
    risk_level = get_risk_level(composite)
    
    return {
        "composite_score": round(composite, 1),
        "risk_level": risk_level,
        "dimension_scores": {
            "security": round(security_score, 1),
            "liquidity": round(liquidity_score, 1),
            "transaction": round(transaction_score, 1)
        }
    }
```

### Step 4: Flag Detection

Identify specific risk flags:

```python
from scripts.flags import RiskFlagDetector

def detect_flags(data: dict, scores: dict) -> list[dict]:
    """Detect specific risk flags."""
    detector = RiskFlagDetector()
    
    flags = []
    
    # Critical flags (auto-fail)
    if data["security_report"].get("mint_authority"):
        flags.append({
            "name": "MINT_ENABLED",
            "severity": "CRITICAL",
            "description": "Mint authority is still enabled - unlimited supply risk",
            "action": "REJECT"
        })
    
    if data["security_report"].get("freeze_authority"):
        flags.append({
            "name": "FREEZE_ENABLED",
            "severity": "CRITICAL",
            "description": "Freeze authority enabled - can freeze all holdings",
            "action": "REJECT"
        })
    
    # Warning flags
    if scores["liquidity"] > 50:
        flags.append({
            "name": "LOW_LIQUIDITY",
            "severity": "WARNING",
            "description": "Liquidity score indicates high risk",
            "action": "CAUTION"
        })
    
    return flags
```

### Step 5: Recommendation Generation

Generate actionable recommendation:

```python
def generate_recommendation(score: float, flags: list) -> str:
    """Generate trading recommendation based on score and flags."""
    
    # Check for critical flags first
    critical_flags = [f for f in flags if f["severity"] == "CRITICAL"]
    if critical_flags:
        flag_names = ", ".join(f["name"] for f in critical_flags)
        return f"DO NOT TRADE - Critical risks: {flag_names}"
    
    # Score-based recommendation
    if score <= 20:
        return "SAFE TO TRADE - Low risk profile"
    elif score <= 40:
        return "PROCEED WITH CAUTION - Medium risk, consider position sizing"
    elif score <= 60:
        return "HIGH RISK - Reduce position size significantly"
    elif score <= 80:
        return "AVOID - High risk, only trade if verified"
    else:
        return "CRITICAL RISK - DO NOT TRADE"
```

---

## Example Commands

### Single Wallet Analysis

```bash
# Full wallet risk profile
python scripts/analyze_wallet.py --wallet 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU

# With custom thresholds
python scripts/analyze_wallet.py \
  --wallet 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU \
  --risk-profile conservative

# Output to file
python scripts/analyze_wallet.py \
  --wallet 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU \
  --output report.json
```

### Token Risk Scoring

```bash
# Score single token
python scripts/score_token.py --mint EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

# Score with LP analysis
python scripts/score_token.py \
  --mint TOKEN_MINT \
  --check-liquidity \
  --pool-address POOL_ADDRESS

# Quick risk check (security only)
python scripts/score_token.py --mint TOKEN_MINT --quick
```

### Batch Operations

```bash
# Analyze multiple wallets
python scripts/batch_analyze.py \
  --wallets wallets.csv \
  --output batch_report.json \
  --parallel 5

# Screen multiple tokens
python scripts/batch_screen.py \
  --mints tokens.txt \
  --min-liquidity 50000 \
  --max-risk 60 \
  --output screened_tokens.json
```

### Pattern Detection

```bash
# Detect wash trading (last 30 days)
python scripts/detect_wash_trading.py \
  --wallet 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU \
  --days 30

# Identify sniper activity
python scripts/detect_sniping.py \
  --wallet 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU \
  --threshold 5

# Check for bundling
python scripts/detect_bundling.py \
  --wallet 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
```

### LP Verification

```bash
# Check LP lock status
python scripts/check_liquidity.py \
  --pool 58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2

# Verify LP lock with expiry
python scripts/check_liquidity.py \
  --pool POOL_ADDRESS \
  --check-expiry \
  --min-lock-days 180
```

---

## Output Interpretation

### JSON Output Structure

```json
{
  "analysis_id": "risk_20260313_143022_abc123",
  "timestamp": "2026-03-13T14:30:22Z",
  "target": {
    "type": "wallet",
    "address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
  },
  "risk_assessment": {
    "composite_score": 35.5,
    "risk_level": "MEDIUM",
    "dimension_scores": {
      "security": 25.0,
      "liquidity": 40.0,
      "transaction": 30.0,
      "holder": 45.0
    }
  },
  "flags": [
    {
      "name": "HIGH_MEME_EXPOSURE",
      "severity": "WARNING",
      "description": "60% of portfolio in high-risk meme tokens",
      "action": "CAUTION"
    }
  ],
  "details": {
    "wallet_age_days": 45,
    "total_transactions": 156,
    "unique_tokens": 8,
    "total_value_usd": "5000.00"
  },
  "recommendation": "PROCEED WITH CAUTION - Medium risk wallet. Consider reducing position size.",
  "data_sources": {
    "rugcheck": true,
    "bitget": true,
    "solana_rpc": true
  },
  "cache_until": "2026-03-13T15:30:22Z"
}
```

### Risk Level Guide

| Risk Level | Score Range | Color | Trading Action |
|------------|-------------|-------|----------------|
| **LOW** | 0-20 | 🟢 | Safe to trade, normal position size |
| **MEDIUM** | 21-40 | 🟡 | Proceed with caution, consider 50% position |
| **ELEVATED** | 41-60 | 🟠 | High risk, reduce to 25% position |
| **HIGH** | 61-80 | 🔴 | Avoid unless verified externally |
| **CRITICAL** | 81-100 | ⚫ | DO NOT TRADE |

### Flag Severity Guide

| Severity | Meaning | Response |
|----------|---------|----------|
| **CRITICAL** | Immediate rejection required | Do not proceed |
| **HIGH** | Severe risk, strong caution | Require external verification |
| **WARNING** | Elevated risk factors | Adjust position sizing |
| **INFO** | Informational only | Monitor for changes |

---

## Safety Rules

### DO ✅

| Rule | Description | Rationale |
|------|-------------|-----------|
| **Always verify before large trades** | Run risk assessment for any trade >10 SOL | Prevents significant losses from rugs |
| **Cross-reference multiple factors** | Never rely on single risk dimension | Holistic view reduces false negatives |
| **Document assessments** | Save all risk reports for audit trail | Compliance and pattern analysis |
| **Respect CRITICAL flags** | Immediately reject tokens with critical flags | Mint/freeze authority are deal-breakers |
| **Use fresh data** | Cache expires after 1 hour | Market conditions change rapidly |
| **Verify LP lock duration** | Minimum 6 months lock recommended | Short locks still enable exit scams |
| **Check holder distribution** | Top 10 holders should be <50% | Concentration enables manipulation |
| **Monitor for flag changes** | Re-check tokens before each trade | Projects can rug after initial safety |

### DO NOT ❌

| Rule | Description | Consequence of Violation |
|------|-------------|--------------------------|
| **Never trade on CRITICAL risk** | Score >80 or critical flags | High probability of total loss |
| **Don't ignore mint authority** | Enabled mint = unlimited supply risk | Dev can dump infinite tokens |
| **Don't trust unlocked LP** | Unlocked = liquidity removal anytime | Classic rug-pull mechanism |
| **Don't chase new tokens blindly** | <24h old tokens have highest rug rate | 90%+ of new tokens fail |
| **Don't share analysis publicly** | Don't reveal your screening criteria | Prevents gaming the system |
| **Don't cache scores >1 hour** | Stale data leads to bad decisions | Projects can change instantly |
| **Don't override risk thresholds** | Configured thresholds exist for reason | Emotional trading causes losses |
| **Don't skip verification step** | Even for "known" safe tokens | Formerly safe projects can rug |

### Red Flag Checklist

Before ANY trade, verify these **critical items**:

```
□ Mint authority = DISABLED (null)
□ Freeze authority = DISABLED (null)
□ LP locked > 6 months
□ Top 10 holders < 50% of supply
□ Pool size > $50,000
□ Token age > 7 days (or verified team)
□ 24h volume > $50,000
□ Buy/sell ratio between 0.5-2.0
□ Contract verified on explorer
□ No blacklist function detected
```

**If ANY box is unchecked → REDUCE POSITION SIZE by 50%**

**If 3+ boxes unchecked → DO NOT TRADE**

### Position Sizing Matrix

| Risk Level | Max Position (% of portfolio) | Example (100 SOL portfolio) |
|------------|-------------------------------|----------------------------|
| LOW (0-20) | 10% | 10 SOL |
| MEDIUM (21-40) | 5% | 5 SOL |
| ELEVATED (41-60) | 2% | 2 SOL |
| HIGH (61-80) | 0.5% | 0.5 SOL |
| CRITICAL (81-100) | 0% | DO NOT TRADE |

---

## Risk Thresholds Configuration

### Built-in Profiles

```yaml
# Conservative - Maximum safety
conservative:
  thresholds:
    low: 15
    medium: 30
    elevated: 45
    high: 60
  requirements:
    min_lp_lock_days: 365
    max_top10_holder_pct: 40
    min_pool_size_usd: 100000
    min_token_age_days: 30

# Balanced - Default (recommended)
balanced:
  thresholds:
    low: 20
    medium: 40
    elevated: 60
    high: 80
  requirements:
    min_lp_lock_days: 180
    max_top10_holder_pct: 50
    min_pool_size_usd: 50000
    min_token_age_days: 7

# Aggressive - Higher risk tolerance
aggressive:
  thresholds:
    low: 25
    medium: 50
    elevated: 65
    high: 85
  requirements:
    min_lp_lock_days: 90
    max_top10_holder_pct: 60
    min_pool_size_usd: 10000
    min_token_age_days: 1
```

### Using Custom Profiles

```bash
# Use conservative profile
python scripts/analyze_wallet.py \
  --wallet ADDRESS \
  --profile conservative

# Custom thresholds via CLI
python scripts/score_token.py \
  --mint TOKEN_MINT \
  --custom-thresholds '{"low": 10, "medium": 25, "high": 50}'
```

---

## Testing

### Unit Tests

```bash
# Run all tests
cd skills/risk-scorer-skill
pytest tests/ -v

# Run specific test file
pytest tests/test_security_scorer.py -v

# Run with coverage
pytest tests/ --cov=scripts --cov-report=html
```

### Integration Tests

```bash
# Testnet wallet analysis
python scripts/analyze_wallet.py \
  --wallet TESTNET_WALLET_ADDRESS \
  --network testnet

# Test with known safe token
python scripts/score_token.py \
  --mint EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --expected-score-max 25

# Test with known risky token
python scripts/score_token.py \
  --mint KNOWN_RUG_TOKEN \
  --expected-score-min 80
```

### Mock Testing

```python
# tests/test_risk_scorer.py
import pytest
from unittest.mock import Mock, patch

def test_critical_flag_detection():
    """Test that critical flags are properly detected."""
    from scripts.flags import RiskFlagDetector
    
    detector = RiskFlagDetector()
    
    # Mock security report with mint authority enabled
    mock_report = {
        "mint_authority": True,
        "freeze_authority": False
    }
    
    flags = detector.detect_critical_flags(mock_report)
    
    assert len(flags) == 1
    assert flags[0]["name"] == "MINT_ENABLED"
    assert flags[0]["severity"] == "CRITICAL"
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Rate limit errors | Too many API requests | Implement backoff, reduce batch size |
| Invalid address format | Wrong address encoding | Verify base58 format for Solana |
| Timeout errors | Network issues | Increase timeout, check connectivity |
| Score = 0 for all | Missing API keys | Verify environment variables |
| Stale data | Cache not expiring | Clear cache, check TTL settings |

### Debug Mode

```bash
# Enable verbose logging
python scripts/analyze_wallet.py \
  --wallet ADDRESS \
  --debug \
  --log-file debug.log
```

### Getting Help

- Documentation: `./docs/`
- Issues: GitHub Issues
- API Status: Check provider status pages

---

## Changelog

### v0.2.0 (Current)
- Added weighted scoring formula documentation
- Expanded API integration guide
- Added position sizing matrix
- New pattern detection scripts

### v0.1.0 (Initial)
- Basic wallet and token scoring
- RugCheck API integration
- Risk flag detection
- JSON output format
