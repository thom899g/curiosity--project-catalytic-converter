"""
Centralized configuration management with validation and type safety.
All configuration should flow through this module.
"""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class ChainConfig:
    """Configuration for a single blockchain"""
    name: str
    rpc_url: str
    ws_url: Optional[str] = None
    chain_id: int = 0
    native_token: str = "ETH"
    gas_limit_multiplier: float = 1.2
    max_priority_fee: int = 2000000000  # 2 Gwei
    max_fee_per_gas: int = 30000000000  # 30 Gwei
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.rpc_url:
            raise ValueError(f"RPC URL required for {self.name}")
        if not self.rpc_url.startswith(("http://", "https://", "ws://", "wss://")):
            raise ValueError(f"Invalid RPC URL format for {self.name}")


@dataclass
class StrategyConfig:
    """Configuration for trading strategies"""
    # Concentrated Liquidity
    cl_min_tick_spacing: int = 60
    cl_max_leverage: float = 2.0
    cl_position_width: float = 0.1  # ±10% around current price
    cl_rebalance_threshold: float = 0.05  # 5% price movement
    
    # Cross-Chain Arbitrage
    arb_min_profit_percentage: float = 0.003
    arb_max_slippage: float = 0.005
    arb_bridge_preference: List[str] = field(default_factory=lambda: ["LayerZero", "Axelar"])
    
    # Capital Efficiency
    lending_protocols: List[str] = field(default_factory=lambda: ["Aave", "Compound"])
    min_collateral_ratio: float = 1.5
    max_utilization_rate: float = 0.8


@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_daily_drawdown: float = 0.05
    var_confidence_level: float = 0.95
    var_lookback_days: int = 30
    peg_deviation_threshold: float = 0.015  # 1.5%
    gas_price_threshold_gwei: int = 100
    position_size_limit_usd: float = 10000
    
    # Circuit Breaker Levels
    circuit_breaker_levels: Dict[str, float] = field(default_factory=lambda: {
        "level_1": 0.02,  # Warning at 2% deviation
        "level_2": 0.03,  # Reduce positions at 3%
        "level_3": 0.05   # Full shutdown at 5%
    })


@dataclass
class FirebaseConfig:
    """Firebase configuration"""
    credentials_path: str = "./firebase_credentials.json"
    project_id: str = ""
    database_url: str = ""
    
    # Collection names
    collections: Dict[str, str] = field(default_factory=lambda: {
        "trades": "trades",
        "portfolio": "portfolio_state",
        "risk_metrics": "risk_metrics",
        "system_health": "system_health",
        "alerts": "alerts"
    })
    
    def __post_init__(self):
        """Validate Firebase configuration"""
        if not os.path.exists(self.credentials_path):
            logger.warning(f"Firebase credentials not found at {self.credentials_path}")
        if not self.project_id:
            logger.warning("Firebase project ID not set")


class Config:
    """Main configuration singleton"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize all configuration sections"""
        # Chain configurations
        self.chains = {
            "polygon": ChainConfig(
                name="polygon",
                rpc_url=os.getenv("POLYGON_RPC_URL", ""),
                ws_url=os.getenv("POLYGON_WS_URL", ""),
                chain_id=137,
                native_token="MATIC"
            ),
            "base": ChainConfig(
                name="base",
                rpc_url=os.getenv("BASE_RPC_URL", ""),
                chain_id=8453,
                native_token="ETH"
            ),
            "arbitrum": ChainConfig(
                name="arbitrum",
                rpc_url=os.getenv("ARBITRUM_RPC_URL", ""),
                chain_id=42161,
                native_token="ETH"
            )
        }
        
        # Strategy configuration
        self.strategy = StrategyConfig()
        
        # Risk configuration
        self.risk = RiskConfig()
        
        # Firebase configuration
        self.firebase = FirebaseConfig(
            credentials_path=os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase_credentials.json"),
            project_id=os.getenv("FIREBASE_PROJECT_ID", "")
        )
        
        # Telegram configuration
        self.telegram = {
            "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
            "chat_id": os.getenv("TELEGRAM_CHAT_ID", "")
        }
        
        # Target configuration
        self.target = {
            "mac_studio_target_usd": 4000,
            "profit_buffer": float(os.getenv("TARGET_PROFIT_BUFFER", "1.2"))
        }
        
        # Validate critical configurations
        self._validate()
    
    def _validate(self):
        """Validate critical configuration values"""
        errors = []
        
        # Check RPC URLs
        for chain_name, chain_config in self.chains.items():
            if not chain_config.rpc_url:
                errors.append(f"RPC URL not set for {chain_name}")
        
        # Check Firebase
        if not self.firebase.project_id:
            errors.append("Firebase project ID not configured")
        
        # Check Telegram if enabled
        if self.telegram["bot_token"] and not self.telegram["chat_id"]:
            errors.append("Telegram chat ID required when bot token is set")
        
        if errors:
            error_msg = "Configuration errors:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def get_active_chains(self) -> List[str]:
        """Get list of chains with valid RPC URLs"""
        return [name for name, config in self.chains.items() if config.rpc_url]


# Global configuration instance
config = Config()