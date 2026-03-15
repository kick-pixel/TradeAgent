#!/usr/bin/env python3
"""
Trading Strategy Script - Strategy execution and management

Provides strategy templates and execution logic for meme coin trading.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "bitget-wallet-skill" / "scripts"))


class StrategyType(Enum):
    MOMENTUM = "momentum"
    DIP_BUY = "dip_buy"
    NEW_LAUNCH = "new_launch"
    TREND_FOLLOW = "trend_follow"
    MEAN_REVERSION = "mean_reversion"


@dataclass
class StrategyConfig:
    """Strategy configuration"""
    name: str
    strategy_type: StrategyType
    min_risk_score: int
    max_position_pct: float
    entry_conditions: Dict[str, Any]
    exit_conditions: Dict[str, Any]
    stop_loss_pct: float
    take_profit_pct: float
    trailing_stop: bool = False
    trailing_stop_pct: float = 10.0
    time_stop_hours: int = 24


@dataclass
class PositionSizing:
    """Position sizing result"""
    max_position_usd: float
    recommended_position_usd: float
    position_pct: float
    risk_adjusted_size: float
    notes: str


class StrategyEngine:
    """Trading strategy engine"""
    
    def __init__(self, portfolio_value: float = 1000.0):
        self.portfolio_value = portfolio_value
        self.strategies = self._init_strategies()
    
    def _init_strategies(self) -> Dict[StrategyType, StrategyConfig]:
        """Initialize default strategies"""
        return {
            StrategyType.MOMENTUM: StrategyConfig(
                name="Momentum Strategy",
                strategy_type=StrategyType.MOMENTUM,
                min_risk_score=60,
                max_position_pct=5.0,
                entry_conditions={
                    "price_change_24h_min": 0.10,
                    "price_change_24h_max": 0.50,
                    "volume_increase_min": 1.0,
                    "buy_ratio_min": 0.55,
                },
                exit_conditions={
                    "profit_target": 0.30,
                    "partial_profit_1": 0.30,
                    "partial_profit_2": 0.50,
                },
                stop_loss_pct=15.0,
                take_profit_pct=30.0,
                trailing_stop=True,
                trailing_stop_pct=10.0,
                time_stop_hours=24,
            ),
            StrategyType.DIP_BUY: StrategyConfig(
                name="Dip Buy Strategy",
                strategy_type=StrategyType.DIP_BUY,
                min_risk_score=70,
                max_position_pct=3.0,
                entry_conditions={
                    "price_change_24h_max": -0.15,
                    "price_change_24h_min": -0.30,
                    "volume_declining": True,
                    "support_level_near": True,
                },
                exit_conditions={
                    "profit_target": 0.20,
                    "resistance_level": True,
                },
                stop_loss_pct=20.0,
                take_profit_pct=20.0,
                trailing_stop=False,
                time_stop_hours=48,
            ),
            StrategyType.NEW_LAUNCH: StrategyConfig(
                name="New Launch Strategy",
                strategy_type=StrategyType.NEW_LAUNCH,
                min_risk_score=50,
                max_position_pct=2.0,
                entry_conditions={
                    "launch_hours_max": 24,
                    "initial_liquidity_min": 10000,
                    "holder_growth": True,
                },
                exit_conditions={
                    "profit_target": 0.50,
                    "time_exit_hours": 4,
                },
                stop_loss_pct=25.0,
                take_profit_pct=50.0,
                trailing_stop=False,
                time_stop_hours=4,
            ),
            StrategyType.TREND_FOLLOW: StrategyConfig(
                name="Trend Following Strategy",
                strategy_type=StrategyType.TREND_FOLLOW,
                min_risk_score=65,
                max_position_pct=4.0,
                entry_conditions={
                    "trend_1h": "bullish",
                    "trend_4h": "bullish",
                    "volume_above_average": True,
                },
                exit_conditions={
                    "trend_reversal": True,
                    "profit_target": 0.40,
                },
                stop_loss_pct=15.0,
                take_profit_pct=40.0,
                trailing_stop=True,
                trailing_stop_pct=15.0,
                time_stop_hours=72,
            ),
        }
    
    def calculate_position_size(self,
                                 risk_score: int,
                                 conviction: str = "medium",
                                 strategy_type: StrategyType = StrategyType.MOMENTUM
                                 ) -> PositionSizing:
        """Calculate optimal position size"""
        
        strategy = self.strategies.get(strategy_type, self.strategies[StrategyType.MOMENTUM])
        
        # Base position from risk score
        if risk_score >= 80:
            base_pct = 5.0
        elif risk_score >= 60:
            base_pct = 3.0
        elif risk_score >= 40:
            base_pct = 2.0
        else:
            base_pct = 0.0
        
        # Adjust for conviction
        conviction_multipliers = {
            "high": 1.5,
            "medium": 1.0,
            "low": 0.5,
        }
        multiplier = conviction_multipliers.get(conviction, 1.0)
        
        # Calculate position
        position_pct = min(base_pct * multiplier, strategy.max_position_pct)
        position_usd = self.portfolio_value * (position_pct / 100)
        
        # Risk-adjusted size (Kelly criterion simplified)
        win_rate = 0.55  # Assumed
        avg_win = strategy.take_profit_pct / 100
        avg_loss = strategy.stop_loss_pct / 100
        
        if avg_loss > 0:
            kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            kelly = max(0, min(kelly, 0.25))  # Cap at 25%
        else:
            kelly = 0
        
        risk_adjusted = position_usd * (1 + kelly)
        
        # Generate notes
        notes_parts = [
            f"Base position ({base_pct}%) adjusted for {conviction} conviction",
            f"Strategy: {strategy.name}",
            f"Max allowed: {strategy.max_position_pct}%",
        ]
        
        if risk_adjusted > position_usd:
            notes_parts.append(f"Kelly criterion suggests +{(risk_adjusted/position_usd-1)*100:.0f}% size increase")
        
        return PositionSizing(
            max_position_usd=self.portfolio_value * (strategy.max_position_pct / 100),
            recommended_position_usd=position_usd,
            position_pct=position_pct,
            risk_adjusted_size=risk_adjusted,
            notes="; ".join(notes_parts)
        )
    
    def evaluate_entry(self,
                       token_data: Dict[str, Any],
                       strategy_type: StrategyType = StrategyType.MOMENTUM
                       ) -> Dict[str, Any]:
        """Evaluate if token meets entry conditions"""
        
        strategy = self.strategies.get(strategy_type)
        if not strategy:
            return {"valid": False, "reason": "Unknown strategy"}
        
        conditions = strategy.entry_conditions
        results = {
            "valid": True,
            "checks": [],
            "strategy": strategy.name,
        }
        
        # Check risk score
        risk_score = token_data.get("risk_score", 0)
        if risk_score < strategy.min_risk_score:
            results["valid"] = False
            results["checks"].append(f"Risk score {risk_score} < {strategy.min_risk_score}")
        else:
            results["checks"].append(f"Risk score {risk_score} >= {strategy.min_risk_score}")
        
        # Check price change
        change_24h = token_data.get("change_24h", 0)
        if "price_change_24h_min" in conditions:
            if change_24h < conditions["price_change_24h_min"]:
                results["valid"] = False
                results["checks"].append(f"Price change {change_24h:.1%} < {conditions['price_change_24h_min']:.1%}")
            else:
                results["checks"].append(f"Price change {change_24h:.1%} >= {conditions['price_change_24h_min']:.1%}")
        
        if "price_change_24h_max" in conditions:
            if change_24h > conditions["price_change_24h_max"]:
                results["valid"] = False
                results["checks"].append(f"Price change {change_24h:.1%} > {conditions['price_change_24h_max']:.1%}")
            else:
                results["checks"].append(f"Price change {change_24h:.1%} <= {conditions['price_change_24h_max']:.1%}")
        
        # Check volume
        volume = token_data.get("volume_24h", 0)
        if volume < 10000:
            results["valid"] = False
            results["checks"].append(f"Volume ${volume:.0f} too low")
        else:
            results["checks"].append(f"Volume ${volume:.0f} OK")
        
        return results
    
    def get_exit_plan(self,
                      entry_price: float,
                      position_size: float,
                      strategy_type: StrategyType = StrategyType.MOMENTUM
                      ) -> Dict[str, Any]:
        """Generate exit plan for position"""
        
        strategy = self.strategies.get(strategy_type, self.strategies[StrategyType.MOMENTUM])
        
        stop_loss_price = entry_price * (1 - strategy.stop_loss_pct / 100)
        take_profit_price = entry_price * (1 + strategy.take_profit_pct / 100)
        
        plan = {
            "entry_price": entry_price,
            "position_size": position_size,
            "stop_loss": {
                "price": stop_loss_price,
                "pct": strategy.stop_loss_pct,
                "loss_usd": position_size * (strategy.stop_loss_pct / 100),
            },
            "take_profit": {
                "price": take_profit_price,
                "pct": strategy.take_profit_pct,
                "profit_usd": position_size * (strategy.take_profit_pct / 100),
            },
            "trailing_stop": {
                "enabled": strategy.trailing_stop,
                "pct": strategy.trailing_stop_pct,
            },
            "time_stop": {
                "hours": strategy.time_stop_hours,
            },
        }
        
        # Add partial exit plan
        if "partial_profit_1" in strategy.exit_conditions:
            tp1 = strategy.exit_conditions["partial_profit_1"]
            plan["partial_exit_1"] = {
                "pct": tp1,
                "price": entry_price * (1 + tp1),
                "sell_pct": 25,
            }
        
        if "partial_profit_2" in strategy.exit_conditions:
            tp2 = strategy.exit_conditions["partial_profit_2"]
            plan["partial_exit_2"] = {
                "pct": tp2,
                "price": entry_price * (1 + tp2),
                "sell_pct": 25,
            }
        
        return plan
    
    def list_strategies(self) -> List[Dict[str, Any]]:
        """List available strategies"""
        return [
            {
                "name": s.name,
                "type": s.strategy_type.value,
                "min_risk_score": s.min_risk_score,
                "max_position_pct": s.max_position_pct,
                "stop_loss_pct": s.stop_loss_pct,
                "take_profit_pct": s.take_profit_pct,
            }
            for s in self.strategies.values()
        ]


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Trading Strategy Engine")
    subparsers = parser.add_subparsers(dest="command")
    
    # List strategies
    subparsers.add_parser("list", help="List available strategies")
    
    # Position sizing
    size_parser = subparsers.add_parser("size", help="Calculate position size")
    size_parser.add_argument("--portfolio", type=float, default=1000, help="Portfolio value")
    size_parser.add_argument("--risk-score", type=int, required=True, help="Token risk score")
    size_parser.add_argument("--conviction", choices=["high", "medium", "low"], default="medium")
    size_parser.add_argument("--strategy", choices=["momentum", "dip_buy", "new_launch"], default="momentum")
    
    # Exit plan
    exit_parser = subparsers.add_parser("exit", help="Generate exit plan")
    exit_parser.add_argument("--entry", type=float, required=True, help="Entry price")
    exit_parser.add_argument("--size", type=float, required=True, help="Position size USD")
    exit_parser.add_argument("--strategy", choices=["momentum", "dip_buy", "new_launch"], default="momentum")
    
    args = parser.parse_args()
    
    if args.command == "list":
        engine = StrategyEngine()
        strategies = engine.list_strategies()
        print(json.dumps(strategies, indent=2))
    
    elif args.command == "size":
        engine = StrategyEngine(portfolio_value=args.portfolio)
        strategy_map = {
            "momentum": StrategyType.MOMENTUM,
            "dip_buy": StrategyType.DIP_BUY,
            "new_launch": StrategyType.NEW_LAUNCH,
        }
        sizing = engine.calculate_position_size(
            risk_score=args.risk_score,
            conviction=args.conviction,
            strategy_type=strategy_map.get(args.strategy, StrategyType.MOMENTUM)
        )
        print(json.dumps(asdict(sizing), indent=2))
    
    elif args.command == "exit":
        engine = StrategyEngine()
        strategy_map = {
            "momentum": StrategyType.MOMENTUM,
            "dip_buy": StrategyType.DIP_BUY,
            "new_launch": StrategyType.NEW_LAUNCH,
        }
        plan = engine.get_exit_plan(
            entry_price=args.entry,
            position_size=args.size,
            strategy_type=strategy_map.get(args.strategy, StrategyType.MOMENTUM)
        )
        print(json.dumps(plan, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
