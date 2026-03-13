# BestTradeAgent - Demo Test Scenarios

**Project**: BestTradeAgent  
**Hackathon**: Solana Agent Economy Hackathon 2026  
**Demo Purpose**: Validate risk-first trading workflow with automated protection and human-in-loop decision making

---

## Scenario 1: Safe Meme Coin Trade ✅

**Setup**: Token with risk score 85/100, good liquidity, no honeypot flags

**Commands**:

```bash
# Step 1: Scan for coins
python -m cli.main scan --limit 5
```

**Expected Output**:
```
Scanning Solana for new tokens...

Found 5 tokens:
  1. SAFE_TOKEN (0x1234...) - Score: 85, Liquidity: $45,000
  2. ANOTHER_TOKEN (0x5678...) - Score: 72, Liquidity: $32,000
  3. EXAMPLE_TOKEN (0xabcd...) - Score: 91, Liquidity: $120,000
  ...

Use 'risk-check --contract <address>' for detailed analysis
```

```bash
# Step 2: Check specific token
python -m cli.main risk-check --chain sol --contract SAFE_TOKEN_ADDRESS
```

**Expected Output**:
```
Token: SAFE_TOKEN
Chain: Solana
Contract: 0x1234...

Risk Analysis:
  Overall Score: 85/100
  Rating: SAFE ✅

Factors:
  ✅ Liquidity: $45,000 (good)
  ✅ Holder distribution: healthy
  ✅ No honeypot detected
  ✅ Contract verified
  ⚠️ Age: 3 days (moderate)

Recommendation: Trade with standard caution
```

```bash
# Step 3: Execute trade
python -m cli.main swap --chain sol --from SOL --to SAFE_TOKEN --amount 0.1
```

**Expected Output**:
```
Trade Details:
  From: 0.1 SOL
  To: ~1,250 SAFE_TOKEN
  Price Impact: 0.3%
  Risk Score: 85/100 (SAFE)

⚠️ Confirm trade? (YES/no): YES

Executing trade...
✅ Trade successful!
Transaction: https://solscan.io/tx/0xabc123...
```

---

## Scenario 2: Dangerous Coin - Auto Blocked 🚫

**Setup**: Token with risk score 25/100, honeypot detected, low liquidity

**Commands**:

```bash
python -m cli.main risk-check --chain sol --contract RISKY_TOKEN_ADDRESS
```

**Expected Output**:
```
Token: SCAM_TOKEN
Chain: Solana
Contract: 0x9999...

Risk Analysis:
  Overall Score: 25/100
  Rating: DANGEROUS 🚫

Critical Risks Detected:
  ❌ Honeypot detected - cannot sell after buy
  ❌ Liquidity: $500 (extremely low)
  ❌ Owner can mint unlimited tokens
  ❌ Blacklist function present
  ❌ Contract not verified

Recommendation: DO NOT TRADE - Auto-blocked
```

```bash
# Attempting trade anyway
python -m cli.main swap --chain sol --from SOL --to SCAM_TOKEN --amount 0.1
```

**Expected Output**:
```
🚫 TRADE BLOCKED

Token SCAM_TOKEN has risk score 25/100 (DANGEROUS)
Critical risks detected: honeypot, unlimited minting

Auto-protection active. Trade not executed.
Use --override flag only if you fully understand the risks.
```

---

## Scenario 3: Moderate Risk - User Decision ⚠️

**Setup**: Token with score 55/100, some warnings but no critical flags

**Commands**:

```bash
python -m cli.main risk-check --chain sol --contract EDGE_TOKEN_ADDRESS
```

**Expected Output**:
```
Token: EDGE_TOKEN
Chain: Solana
Contract: 0xedge...

Risk Analysis:
  Overall Score: 55/100
  Rating: CAUTION ⚠️

Warnings:
  ⚠️ Liquidity: $8,000 (moderate)
  ⚠️ Age: 12 hours (new)
  ⚠️ Top 10 holders: 45% supply
  ✅ No honeypot detected
  ✅ Contract verified

Recommendation: Small trades only, monitor closely
```

```bash
python -m cli.main swap --chain sol --from SOL --to EDGE_TOKEN --amount 0.1
```

**Expected Output**:
```
⚠️ WARNING: Moderate Risk Token

Trade Details:
  From: 0.1 SOL
  To: ~500 EDGE_TOKEN
  Price Impact: 1.2%
  Risk Score: 55/100 (CAUTION)

Warnings:
  - New token (12 hours old)
  - Concentrated ownership
  - Moderate liquidity

This is a higher-risk trade. Proceed with caution.
⚠️ Confirm trade? (YES/no): [User decides]
```

**If user enters NO**:
```
Trade cancelled by user.
```

**If user enters YES**:
```
Executing high-risk trade...
✅ Trade successful!
Transaction: https://solscan.io/tx/0xedge123...

Reminder: Monitor this position closely.
```

---

## Summary Table

| Scenario | Risk Score | Rating | Result | Key Learning |
|----------|------------|--------|--------|--------------|
| Safe Coin | 85 | SAFE ✅ | Executes | Risk-first workflow enables confident trades |
| Dangerous | 25 | DANGEROUS 🚫 | Auto-blocked | System protects users from scams |
| Edge Case | 55 | CAUTION ⚠️ | User decides | Human-in-loop for moderate risks |

---

## Demo Flow Recommendations

1. **Start with Scenario 1** - Show the happy path, build confidence
2. **Move to Scenario 2** - Demonstrate protection value
3. **End with Scenario 3** - Highlight user control and transparency

**Total Demo Time**: ~5 minutes

**Key Messages**:
- Risk scoring happens automatically before every trade
- Dangerous tokens are blocked by default
- Users retain control for moderate-risk decisions
- All risk factors are transparent and explained
