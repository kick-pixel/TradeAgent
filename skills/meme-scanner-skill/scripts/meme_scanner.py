#!/usr/bin/env python3
"""
Meme Scanner Script - Automated token discovery and analysis

This script provides programmatic access to meme token scanning capabilities.
Can be used standalone or as part of the agent skills framework.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Add parent skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "bitget-wallet-skill" / "scripts"))

from bitget_agent_api import rankings, historical_coins, tx_info, token_info, liquidity, security


class MemeScanner:
    """Scanner for discovering and analyzing meme tokens"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
    
    def get_trending_tokens(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending tokens from Hotpicks"""
        result = rankings(name="Hotpicks")
        if result.get("status") == 0:
            tokens = result.get("data", {}).get("list", [])
            # Filter for Solana only
            return [t for t in tokens if t.get("chain") == "sol"][:limit]
        return []
    
    def get_top_gainers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top gaining tokens"""
        result = rankings(name="topGainers")
        if result.get("status") == 0:
            tokens = result.get("data", {}).get("list", [])
            return [t for t in tokens if t.get("chain") == "sol"][:limit]
        return []
    
    def get_new_launches(self, hours_back: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently launched tokens"""
        # Calculate timestamp
        target_time = datetime.now() - timedelta(hours=hours_back)
        time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")
        
        result = historical_coins(create_time=time_str, limit=limit)
        if result.get("status") == 0:
            return result.get("data", {}).get("list", [])
        return []
    
    def analyze_token(self, contract: str, chain: str = "sol") -> Dict[str, Any]:
        """Comprehensive token analysis"""
        analysis = {
            "contract": contract,
            "chain": chain,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Get basic info
        info_result = token_info(chain=chain, contract=contract)
        if info_result.get("status") == 0:
            analysis["info"] = info_result.get("data", {})
        
        # Get security data
        security_result = security(chain=chain, contract=contract)
        if security_result.get("status") == 0:
            data = security_result.get("data", [])
            if data and isinstance(data, list):
                analysis["security"] = data[0]
            else:
                analysis["security"] = data if isinstance(data, dict) else {}
        
        # Get liquidity
        liquidity_result = liquidity(chain=chain, contract=contract)
        if liquidity_result.get("status") == 0:
            liq_data = liquidity_result.get("data", {})
            if isinstance(liq_data, dict):
                analysis["liquidity"] = {
                    "total_lp_value": liq_data.get("totalLpValue", 0),
                    "locked_lp_value": liq_data.get("lockedLpValue", 0),
                    "locked_percent": liq_data.get("lockedLpPercent", 0),
                }
        
        # Get transaction data
        tx_result = tx_info(chain=chain, contract=contract)
        if tx_result.get("status") == 0:
            tx_data = tx_result.get("data", {})
            if isinstance(tx_data, dict):
                txn_info = tx_data.get("txn_info", {})
                analysis["activity"] = {
                    "volume_24h": txn_info.get("24h", {}).get("volume", 0),
                    "buyers_24h": txn_info.get("24h", {}).get("buyers", 0),
                    "sellers_24h": txn_info.get("24h", {}).get("sellers", 0),
                    "txns_24h": txn_info.get("24h", {}).get("txns", 0),
                }
        
        return analysis
    
    def calculate_momentum_score(self, token: Dict[str, Any]) -> float:
        """Calculate momentum score (0-100)"""
        score = 0.0
        
        # Price change
        change_24h = token.get("change24h", 0)
        if change_24h > 0.5:  # > 50%
            score += 30
        elif change_24h > 0.2:  # > 20%
            score += 20
        elif change_24h > 0.05:  # > 5%
            score += 10
        
        # Volume
        volume = token.get("volume24h", 0)
        if volume > 1000000:  # > $1M
            score += 30
        elif volume > 100000:  # > $100K
            score += 20
        elif volume > 10000:  # > $10K
            score += 10
        
        # Turnover ratio (volume/market cap proxy)
        turnover = token.get("turnover24h", 0)
        if turnover > 10000000:  # > $10M
            score += 20
        elif turnover > 1000000:  # > $1M
            score += 10
        
        # Risk level
        risk = token.get("risk_level", "medium")
        if risk == "low":
            score += 20
        elif risk == "medium":
            score += 10
        
        return min(score, 100)
    
    def find_opportunities(self, 
                          min_momentum: float = 50,
                          min_liquidity: float = 10000,
                          max_positions: int = 5) -> List[Dict[str, Any]]:
        """Find trading opportunities"""
        opportunities = []
        
        # Get trending tokens
        trending = self.get_trending_tokens(limit=20)
        
        for token in trending:
            contract = token.get("contract", "")
            if not contract:
                continue
            
            # Quick liquidity check
            liq_result = liquidity(chain="sol", contract=contract)
            if liq_result.get("status") == 0:
                liq_data = liq_result.get("data", {})
                if isinstance(liq_data, dict):
                    total_liq = liq_data.get("totalLpValue", 0)
                    if total_liq < min_liquidity:
                        continue
                    token["liquidity_usd"] = total_liq
            
            # Calculate momentum
            momentum = self.calculate_momentum_score(token)
            if momentum >= min_momentum:
                token["momentum_score"] = momentum
                opportunities.append(token)
        
        # Sort by momentum
        opportunities.sort(key=lambda x: x.get("momentum_score", 0), reverse=True)
        return opportunities[:max_positions]


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Meme Token Scanner")
    parser.add_argument("command", choices=["trending", "gainers", "new", "analyze", "opportunities"])
    parser.add_argument("--contract", help="Token contract for analysis")
    parser.add_argument("--limit", type=int, default=10, help="Number of results")
    parser.add_argument("--min-momentum", type=float, default=50, help="Minimum momentum score")
    
    args = parser.parse_args()
    
    scanner = MemeScanner()
    
    if args.command == "trending":
        tokens = scanner.get_trending_tokens(limit=args.limit)
        print(json.dumps(tokens, indent=2))
    
    elif args.command == "gainers":
        tokens = scanner.get_top_gainers(limit=args.limit)
        print(json.dumps(tokens, indent=2))
    
    elif args.command == "new":
        tokens = scanner.get_new_launches(limit=args.limit)
        print(json.dumps(tokens, indent=2))
    
    elif args.command == "analyze":
        if not args.contract:
            print("Error: --contract required for analyze", file=sys.stderr)
            sys.exit(1)
        analysis = scanner.analyze_token(args.contract)
        print(json.dumps(analysis, indent=2))
    
    elif args.command == "opportunities":
        opportunities = scanner.find_opportunities(
            min_momentum=args.min_momentum,
            max_positions=args.limit
        )
        print(json.dumps(opportunities, indent=2))


if __name__ == "__main__":
    main()
