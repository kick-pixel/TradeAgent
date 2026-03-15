#!/usr/bin/env python3
"""
Risk Scorer Script - Token security and risk assessment

Provides comprehensive risk scoring for Solana meme tokens.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "bitget-wallet-skill" / "scripts"))

from bitget_agent_api import security, liquidity, check_swap_token


@dataclass
class RiskScore:
    """Risk score result"""
    total: int
    security: int
    liquidity: int
    activity: int
    breakdown: list
    level: str
    recommendation: str


class RiskScorer:
    """Risk assessment engine for meme tokens"""
    
    # Risk level thresholds
    LOW_RISK = 80
    MEDIUM_RISK = 60
    HIGH_RISK = 40
    
    def __init__(self):
        self.weights = {
            "security": 0.4,
            "liquidity": 0.3,
            "activity": 0.3,
        }
    
    def calculate_security_score(self, security_data: Dict[str, Any]) -> Tuple[int, list]:
        """Calculate security score (0-100)"""
        score = 0
        breakdown = []
        
        # Critical checks
        if security_data.get("highRisk", False):
            return 0, ["HIGH RISK TOKEN - AVOID"]
        
        if security_data.get("isHoneypot", False):
            return 0, ["HONEYPOT DETECTED - AVOID"]
        
        # No honeypot (30 points)
        score += 30
        breakdown.append("No honeypot: +30")
        
        # Tax analysis (30 points)
        buy_tax = float(security_data.get("buyTax", 0) or 0)
        sell_tax = float(security_data.get("sellTax", 0) or 0)
        
        if buy_tax == 0 and sell_tax == 0:
            score += 30
            breakdown.append(f"No taxes: +30")
        elif buy_tax <= 5 and sell_tax <= 5:
            score += 25
            breakdown.append(f"Low taxes ({buy_tax}%/{sell_tax}%): +25")
        elif buy_tax <= 10 and sell_tax <= 10:
            score += 15
            breakdown.append(f"Medium taxes ({buy_tax}%/{sell_tax}%): +15")
        else:
            score += 5
            breakdown.append(f"High taxes ({buy_tax}%/{sell_tax}%): +5")
        
        # Contract verification (20 points)
        if security_data.get("isOpenSource", False):
            score += 20
            breakdown.append("Open source: +20")
        else:
            breakdown.append("Closed source: +0")
        
        # Authority checks (20 points)
        freeze_auth = security_data.get("freezeAuth", False)
        mint_auth = security_data.get("mintAuth", False)
        
        if not freeze_auth and not mint_auth:
            score += 20
            breakdown.append("No dangerous authorities: +20")
        elif not freeze_auth or not mint_auth:
            score += 10
            breakdown.append("One dangerous authority: +10")
        else:
            breakdown.append("Both authorities present: +0")
        
        return score, breakdown
    
    def calculate_liquidity_score(self, liquidity_usd: float) -> Tuple[int, list]:
        """Calculate liquidity score (0-100)"""
        score = 0
        breakdown = []
        
        if liquidity_usd >= 1000000:  # $1M+
            score = 100
            breakdown.append(f"Excellent liquidity (${liquidity_usd/1e6:.1f}M): 100")
        elif liquidity_usd >= 500000:  # $500K+
            score = 80
            breakdown.append(f"Very good liquidity (${liquidity_usd/1e3:.0f}K): 80")
        elif liquidity_usd >= 100000:  # $100K+
            score = 60
            breakdown.append(f"Good liquidity (${liquidity_usd/1e3:.0f}K): 60")
        elif liquidity_usd >= 50000:  # $50K+
            score = 40
            breakdown.append(f"Moderate liquidity (${liquidity_usd/1e3:.0f}K): 40")
        elif liquidity_usd >= 10000:  # $10K+
            score = 20
            breakdown.append(f"Low liquidity (${liquidity_usd/1e3:.0f}K): 20")
        else:
            score = 0
            breakdown.append(f"Insufficient liquidity (${liquidity_usd:.0f}): 0")
        
        return score, breakdown
    
    def calculate_activity_score(self, 
                                  volume_24h: float,
                                  buyers: int,
                                  sellers: int) -> Tuple[int, list]:
        """Calculate activity score (0-100)"""
        score = 0
        breakdown = []
        
        # Volume score (50 points)
        if volume_24h >= 10000000:  # $10M+
            score += 50
            breakdown.append(f"High volume (${volume_24h/1e6:.1f}M): +50")
        elif volume_24h >= 1000000:  # $1M+
            score += 40
            breakdown.append(f"Good volume (${volume_24h/1e6:.1f}M): +40")
        elif volume_24h >= 100000:  # $100K+
            score += 25
            breakdown.append(f"Moderate volume (${volume_24h/1e3:.0f}K): +25")
        elif volume_24h >= 10000:  # $10K+
            score += 10
            breakdown.append(f"Low volume (${volume_24h/1e3:.0f}K): +10")
        else:
            breakdown.append(f"Very low volume (${volume_24h:.0f}): +0")
        
        # Buy/sell ratio (30 points)
        total = buyers + sellers
        if total > 0:
            buy_ratio = buyers / total
            if buy_ratio >= 0.6:
                score += 30
                breakdown.append(f"Bullish ratio ({buy_ratio:.0%}): +30")
            elif buy_ratio >= 0.5:
                score += 20
                breakdown.append(f"Neutral ratio ({buy_ratio:.0%}): +20")
            elif buy_ratio >= 0.4:
                score += 10
                breakdown.append(f"Bearish ratio ({buy_ratio:.0%}): +10")
            else:
                breakdown.append(f"Heavy selling ({buy_ratio:.0%}): +0")
        
        # Trader count (20 points)
        if total >= 5000:
            score += 20
            breakdown.append(f"High activity ({total} traders): +20")
        elif total >= 1000:
            score += 15
            breakdown.append(f"Good activity ({total} traders): +15")
        elif total >= 500:
            score += 10
            breakdown.append(f"Moderate activity ({total} traders): +10")
        elif total >= 100:
            score += 5
            breakdown.append(f"Low activity ({total} traders): +5")
        else:
            breakdown.append(f"Very low activity ({total} traders): +0")
        
        return score, breakdown
    
    def assess_token(self, 
                     contract: str,
                     symbol: str = "",
                     chain: str = "sol") -> RiskScore:
        """Complete token risk assessment"""
        
        # Get security data
        sec_result = security(chain=chain, contract=contract)
        if sec_result.get("status") == 0:
            data = sec_result.get("data", [])
            if data and isinstance(data, list):
                sec_data = data[0]
            else:
                sec_data = data if isinstance(data, dict) else {}
        else:
            sec_data = {}
        
        # Calculate security score
        sec_score, sec_breakdown = self.calculate_security_score(sec_data)
        
        # Get liquidity
        liq_result = liquidity(chain=chain, contract=contract)
        if liq_result.get("status") == 0:
            liq_data = liq_result.get("data", {})
            if isinstance(liq_data, dict):
                liquidity_usd = liq_data.get("totalLpValue", 0)
            else:
                liquidity_usd = 0
        else:
            liquidity_usd = 0
        
        # Calculate liquidity score
        liq_score, liq_breakdown = self.calculate_liquidity_score(liquidity_usd)
        
        # For activity, we'd need tx_info - simplified here
        act_score = 50  # Default moderate
        act_breakdown = ["Activity data not fully available: 50"]
        
        # Calculate weighted total
        total = int(
            sec_score * self.weights["security"] +
            liq_score * self.weights["liquidity"] +
            act_score * self.weights["activity"]
        )
        
        # Determine level and recommendation
        if total >= self.LOW_RISK:
            level = "LOW"
            recommendation = "SAFE TO TRADE"
        elif total >= self.MEDIUM_RISK:
            level = "MEDIUM"
            recommendation = "TRADE WITH CAUTION"
        elif total >= self.HIGH_RISK:
            level = "HIGH"
            recommendation = "AVOID OR MINIMAL EXPOSURE"
        else:
            level = "VERY HIGH"
            recommendation = "DO NOT TRADE"
        
        # Combine breakdown
        breakdown = [
            f"Security ({sec_score} x {self.weights['security']}): {int(sec_score * self.weights['security'])}",
            *sec_breakdown,
            f"Liquidity ({liq_score} x {self.weights['liquidity']}): {int(liq_score * self.weights['liquidity'])}",
            *liq_breakdown,
            f"Activity ({act_score} x {self.weights['activity']}): {int(act_score * self.weights['activity'])}",
            *act_breakdown,
        ]
        
        return RiskScore(
            total=total,
            security=sec_score,
            liquidity=liq_score,
            activity=act_score,
            breakdown=breakdown,
            level=level,
            recommendation=recommendation
        )
    
    def format_report(self, contract: str, score: RiskScore) -> str:
        """Format risk report"""
        lines = [
            f"Risk Assessment for {contract}",
            "=" * 50,
            f"",
            f"Overall Score: {score.total}/100",
            f"Risk Level: {score.level}",
            f"Recommendation: {score.recommendation}",
            f"",
            "Component Scores:",
            f"  Security: {score.security}/100",
            f"  Liquidity: {score.liquidity}/100",
            f"  Activity: {score.activity}/100",
            f"",
            "Detailed Breakdown:",
        ]
        for item in score.breakdown:
            lines.append(f"  - {item}")
        
        return "\n".join(lines)


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Token Risk Scorer")
    parser.add_argument("contract", help="Token contract address")
    parser.add_argument("--chain", default="sol", help="Chain code")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    scorer = RiskScorer()
    score = scorer.assess_token(args.contract, chain=args.chain)
    
    if args.json:
        result = {
            "contract": args.contract,
            "score": score.total,
            "security": score.security,
            "liquidity": score.liquidity,
            "activity": score.activity,
            "level": score.level,
            "recommendation": score.recommendation,
            "breakdown": score.breakdown,
        }
        print(json.dumps(result, indent=2))
    else:
        print(scorer.format_report(args.contract, score))


if __name__ == "__main__":
    main()
