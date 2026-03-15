"""
Agent Configuration Management
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class TradingConfig(BaseModel):
    """Trading parameters configuration"""
    default_slippage: float = Field(default=1.0, description="Default slippage tolerance (%)")
    min_liquidity_usd: float = Field(default=10000, description="Minimum liquidity threshold (USD)")
    min_risk_score: int = Field(default=50, description="Minimum risk score (0-100, higher is safer)")
    max_position_pct: float = Field(default=5.0, description="Max position as % of total portfolio")
    max_daily_trades: int = Field(default=5, description="Maximum trades per day")
    max_holdings: int = Field(default=3, description="Maximum concurrent token holdings")
    stop_loss_pct: float = Field(default=15.0, description="Stop loss percentage")
    take_profit_pct: float = Field(default=30.0, description="Take profit percentage")
    max_hold_hours: int = Field(default=24, description="Maximum holding time in hours")


class LLMConfig(BaseModel):
    """LLM configuration"""
    base_url: Optional[str] = Field(default=None, description="OpenAI-compatible API base URL")
    api_key: Optional[str] = Field(default=None, description="API key")
    model: str = Field(default="gpt-4o", description="Model name")
    temperature: float = Field(default=0.1, description="Temperature for trading decisions")
    max_tokens: int = Field(default=4096, description="Max tokens per response")


class WalletConfig(BaseModel):
    """Wallet configuration"""
    solana_rpc_url: str = Field(default="https://api.mainnet-beta.solana.com")
    helius_api_key: Optional[str] = Field(default=None)
    # Mnemonic is loaded from secure storage, never stored in config


class Config(BaseModel):
    """Main configuration"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    wallet: WalletConfig = Field(default_factory=WalletConfig)
    skills_path: Path = Field(default=Path("./skills"))
    log_level: str = Field(default="INFO")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        return cls(
            llm=LLMConfig(
                base_url=os.getenv("OPENAI_BASE_URL") or None,
                api_key=os.getenv("OPENAI_API_KEY") or None,
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            ),
            trading=TradingConfig(
                default_slippage=float(os.getenv("DEFAULT_SLIPPAGE", "1.0")),
                min_liquidity_usd=float(os.getenv("MIN_LIQUIDITY_USD", "10000")),
                min_risk_score=int(os.getenv("MIN_RISK_SCORE", "50")),
            ),
            wallet=WalletConfig(
                solana_rpc_url=os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
                helius_api_key=os.getenv("HELIUS_API_KEY") or None,
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


# Global config instance
config = Config.from_env()
