"""
Main orchestrator for Project Catalytic Converter.
Coordinates all strategies, manages risk, and handles system lifecycle.
"""
import asyncio
import logging
import signal
import sys
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from config import config
from utils.firebase_client import FirebaseClient
from utils.web3_client import Web3MultiChainClient
from risk_oracle.risk_oracle import RiskOracle
from strategies.concentrated_liquidity import ConcentratedLiquidityStrategy
from strategies.cross_chain_arb import CrossChainArbitrageStrategy
from strategies.capital_efficiency import CapitalEfficiencyStrategy
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator that manages all strategies and system lifecycle.
    
    Responsibilities:
    1. Initialize and coordinate all strategy modules
    2. Manage risk via RiskOracle
    3. Handle graceful shutdown
    4. Monitor system health
    5. Coordinate profit compounding and rebalancing
    """
    
    def __init__(self):
        """Initialize the orchestrator with all required components."""
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # Initialize clients
        logger.info("Initializing system components...")
        self.firebase = FirebaseClient()
        self.web3_client = Web3MultiChainClient()
        self.risk_oracle = RiskOracle(self.firebase, self.web3_client)
        
        # Initialize strategies
        self.strategies: Dict[str, object] = {}
        self._init_strategies()
        
        # Performance tracking
        self.last_rebalance = datetime.now()
        self.performance_metrics = {}
        
        # Register signal handlers
        self._register_signal_handlers()
    
    def _init_strategies(self):
        """Initialize all trading strategies."""
        try:
            # Concentrated Liquidity (Primary strategy)
            self.strategies["concentrated_liquidity"] = ConcentratedLiquidityStrategy(
                web3_client=self.web3_client,
                firebase_client=self.firebase,
                risk_oracle=self.risk_oracle
            )
            logger.info("Initialized ConcentratedLiquidityStrategy")
            
            # Cross-Chain Arbitrage (Opportunistic)
            self.strategies["cross_chain_arb"] = CrossChainArbitrageStrategy(
                web3_client=self.web3_client,
                firebase_client=self.firebase,
                risk_oracle=self.risk_oracle
            )
            logger.info("Initialized CrossChainArbitrageStrategy")
            
            # Capital Efficiency (Background optimization)
            self.strategies["capital_efficiency"] = CapitalEfficiencyStrategy(
                web3_client=self.web3_client,
                firebase_client=self.firebase,
                risk_oracle=self.risk_oracle
            )
            logger.info("Initialized CapitalEfficiencyStrategy")
            
        except Exception as e:
            logger.error(f"Failed to initialize strategies: {e}")
            raise
    
    def