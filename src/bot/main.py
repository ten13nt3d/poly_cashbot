#!/usr/bin/env python3
"""
XRP Polymarket Cash Bot - Main Execution Engine

Ultra-selective trading bot optimized for >70% win rate with
scalable capital support from $10 to $1000+.
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional

from src.lib.sentiment.analyzer import TemporalArbitrageDetector, TemporalArbitrageOpportunity
from src.lib.whale.detector import WhaleDetector, OrderbookSnapshot
from src.lib.strategy.interval_strategy import IntervalStrategy, Position, ExitStrategy
from src.lib.risk.manager import ScalableRiskManager
from src.services.polymarket import PolymarketClient
from src.services.price_feed import PriceFeedService
from src.services.market_discovery import MarketDiscoveryService
from src.database import DatabaseManager
from src.models.position import Position as DBPosition
from src.models.trade import Trade as DBTrade
from sqlalchemy import select, func

import logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class CashBot:
    """
    Main bot execution engine.
    
    Implements all core strategies:
    1. High-accuracy sentiment analysis (>80% confidence only)
    2. Whale detection & front-running
    3. 15-minute interval trading with dynamic exits
    4. Scalable risk management for $10-$1000+ capital
    """
    
    def __init__(self, total_capital: Decimal, paper_trading: bool = True):
        """Initialize the cash bot with capital."""
        self.total_capital = total_capital
        self.available_capital = total_capital
        self.paper_trading = paper_trading

        # Initialize core components with temporal arbitrage focus
        self.arbitrage_detector = TemporalArbitrageDetector()
        self.whale_detector = WhaleDetector("XRP_markets")
        self.strategy = IntervalStrategy()
        self.risk_manager = ScalableRiskManager(total_capital)

        # Initialize services
        self.db_manager = DatabaseManager()
        self.polymarket = PolymarketClient(paper_trading=paper_trading)
        self.price_feed = PriceFeedService()
        self.market_discovery = MarketDiscoveryService(
            polymarket_client=self.polymarket,
            db_manager=self.db_manager
        )

        # State tracking
        self.is_running = False
        self.stats = {
            'start_time': None,
            'total_trades': 0,
            'signals_generated': 0,
            'signals_executed': 0
        }

        mode = "PAPER TRADING" if paper_trading else "LIVE TRADING"
        logger.info(
            f"Cash bot initialized ({mode})",
            capital=float(total_capital),
            tier=self.risk_manager.tier
        )

    async def start(self) -> None:
        """Start the trading bot."""
        self.is_running = True
        self.stats['start_time'] = asyncio.get_event_loop().time()
        
        logger.info("Cash bot started", capital=float(self.total_capital))
        
        try:
            await self._main_loop()
        except Exception as e:
            logger.error(f"Bot error: {e}")
            raise
        finally:
            self.is_running = False
            logger.info("Cash bot stopped")

    async def _main_loop(self) -> None:
        """Main trading loop with 15-second intervals."""
        while self.is_running:
            try:
                # 1. Analyze markets forTrading opportunities
                await self._analyze_markets()
                
                # 2. Check for whale opportunities
                await self._check_whale_alerts()
                
                # 3. Monitor existing positions
                await self._monitor_positions()
                
                # 4. Risk management check
                await self._check_risk_limits()
                
                # 5. Sleep for 15 seconds
                await asyncio.sleep(15)
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                # Continue running even after errors
                continue

   async def _analyze_markets(self) -> None:
        """Analyze markets for temporal arbitrage opportunities."""
        try:
            # Fetch real-time spot data (Binance, Coinbase, Kraken)
            spot_data = await self._fetch_spot_data()
            
            # Fetch Polymarket data
            polymarket_data = await self._fetch_polymarket_data()
            
            if not spot_data or not polymarket_data:
                return
            
            # Check each asset for arbitrage opportunities
            for asset in self.arbitrage_detector.ASSETS:
                if asset in spot_data and asset in polymarket_data:
                    opportunity = self.arbitrage_detector.detect_arbitrage_opportunity(
                        spot_data[asset],
                        polymarket_data[asset],
                        asset
                    )
                    
                    self.stats['signals_generated'] += 1
                    
                    if opportunity:
                        logger.info(
                            f"Temporal arbitrage opportunity: {asset}",
                            direction=opportunity.direction,
                            lag=f"{opportunity.polymarket_lag:.1f}s",
                            confidence=opportunity.confidence,
                            urgency=opportunity.urgency
                        )
                        
                        # Should trade if arbitrage is clear
                        if opportunity.confidence > 0.90 and opportunity.polymarket_lag > 30:
                            # Fixed position size (like the successful bot)
                            position_size = Decimal("5000")
                            
                            # Risk check
                            risk_check = self.risk_manager.validate_order(position_size)
                            if risk_check.passed:
                                # Execute arbitrage trade
                                await self._execute_arbitrage(opportunity, position_size)
                            else:
                                logger.info(f"Arbitrage rejected by risk: {risk_check.reason}")
            else:
                logger.debug("No temporal arbitrage opportunities detected")
                
        except Exception as e:
            logger.error(f"Error analyzing markets: {e}")

    async def _execute_trade(self, signal, position_size: Decimal) -> None:
        """Execute a trading position."""
        try:
            # Mock execution (replace with real Polymarket API call)
            entry_price = Decimal("0.55")  # Mock price
            position = self.strategy.create_position(
                market_id="XRP_UP_15min",
                side=signal.direction.lower(),
                size=position_size,
                entry_price=entry_price,
                sentiment_score=signal.sentiment_score,
                confidence=signal.confidence
            )
            
            # Update capital
            self.available_capital -= position_size
            
            # Track position in risk manager
            self.risk_manager.add_position(f"pos_{self.stats['total_trades']}", position_size)
            
            self.stats['signals_executed'] += 1
            
            logger.info(
                f"Position opened: {signal.direction}",
                size=float(position_size),
                price=float(entry_price),
                confidence=signal.confidence
            )
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")

    async def _check_whale_alerts(self) -> None:
        """Monitor for whale trading opportunities."""
        try:
            # Fetch current orderbook (mock)
            orderbook_snapshot = await self._fetch_orderbook()
            
            if orderbook_snapshot:
                alerts = self.whale_detector.update_orderbook_snapshot(orderbook_snapshot)
                
                for alert in alerts:
                    logger.info(
                        f"Whale detected: {alert.side}",
                        size=float(alert.order_size),
                        impact=alert.expected_impact
                    )
                    
                    # Check if we should front-run this whale
                    if alert.confidence > 0.75 and alert.expected_impact > self.whale_detector.MIN_IMPACT_THRESHOLD:
                        position_size = self.whale_detector.calculate_front_run_position_size(
                            alert, self.available_capital
                        )
                        
                        if position_size > Decimal("0"):
                            # Create front-running position
                            await self._execute_front_run(alert, position_size)
                            
        except Exception as e:
            logger.error(f"Error checking whale alerts: {e}")

    async def _execute_arbitrage(self, opportunity: TemporalArbitrageOpportunity, position_size: Decimal) -> None:
        """Execute temporal arbitrage position."""
        try:
            # Calculate entry price (use current Polymarket price)
            current_price = opportunity.polymarket_price
            
            # Create position for arbitrage
            position = self.strategy.create_position(
                market_id=f"{opportunity.direction}_{opportunity.urgency}_{self.stats['total_trades']}",
                side=opportunity.direction.lower(),
                size=position_size,
                entry_price=Decimal(str(current_price)),
                sentiment_score=opportunity.spot_momentum,
                confidence=opportunity.confidence
            )
            
            # Update capital
            self.available_capital -= position_size
            
            # Track position in risk manager
            position_id = f"arb_{opportunity.urgency}_{self.stats['total_trades']}"
            self.risk_manager.add_position(position_id, position_size)
            
            self.stats['signals_executed'] += 1
            
            logger.info(
                f"Arbitrage opportunity exploited: {opportunity.direction}",
                lag=f"{opportunity.polymarket_lag:.1f}s",
                size=float(position_size),
                price=current_price,
                confidence=opportunity.confidence
            )
            
        except Exception as e:
            logger.error(f"Error executing arbitrage: {e}")
        """Execute front-running trade based on whale detection."""
        try:
            # Determine trade direction (opposite of whale's direction)
            trade_side = "sell" if alert.side == "buy" else "buy"
            trade_direction = "SELL" if alert.side == "buy" else "BUY"
            
            logger.info(
                f"Executing whale front-run: {trade_side}",
                size=float(position_size),
                whale_size=float(alert.order_size)
            )
            
            # Create position for front-run
            position = self.strategy.create_position(
                market_id=f"whale_frontrun_{self.stats['total_trades']}",
                side=trade_side,
                size=position_size,
                entry_price=Decimal("0.55"),
                sentiment_score=70 if trade_side == "buy" else -70,
                confidence=alert.confidence
            )
            
            self.available_capital -= position_size
            self.risk_manager.add_position(f"whale_{self.stats['total_trades']}", position_size)
            
            logger.info(f"Front-run position opened: {trade_direction.upper()}")
            
        except Exception as e:
            logger.error(f"Error executing front-run: {e}")

    async def _monitor_positions(self) -> None:
        """Monitor and manage existing positions."""
        # Mock - would fetch real market prices and check position exits
        for position in list(self.strategy.open_positions):
            try:
                # Get current price (mock)
                if position.side == "buy":
                    current_price = Decimal("0.56")  # Price went up
                else:
                    current_price = Decimal("0.54")  # Price went down
                
                # Calculate exit strategy
                exit_strategy = self.strategy.calculate_exit_strategy(
                    position=position,
                    current_price=current_price,
                    current_sentiment=50,  # Mock sentiment
                    market_volatility=0.15
                )
                
                # Execute exit if needed
                if exit_strategy.type != "HOLD":
                    await self._close_position(position, current_price, exit_strategy.reason)
                    
            except Exception as e:
                logger.error(f"Error monitoring position {position.market_id}: {e}")

    async def _close_position(self, position, exit_price: Decimal, reason: str) -> None:
        """Close a position and update state."""
        try:
            trade = self.strategy.close_position(position, exit_price, reason)
            
            # Update available capital
            self.available_capital += Decimal(str(trade['size'])) + Decimal(str(trade['pnl']))
            
            # Update risk manager
            self.risk_manager.remove_position(position.market_id)
            
            # Update statistics
            self.stats['total_trades'] += 1
            
            logger.info(
                f"Position closed: {position.side}",
                pnl=float(trade['pnl']),
                roi_pct=trade['roi_pct'],
                reason=reason
            )
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")

    async def _check_risk_limits(self) -> None:
        """Check and enforce risk management limits."""
        try:
            circuit_breaker = self.risk_manager.check_circuit_breaker()
            if circuit_breaker:
                logger.critical(f"Circuit breaker triggered: {circuit_breaker}")
                self.is_running = False
                return
                
            # Check daily metrics
            summary = self.risk_manager.get_risk_summary()
            if summary['consecutive_losses'] >= 3:
                logger.warning(f"Consecutive losses: {summary['consecutive_losses']}")
                
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")

    # Mock data methods (would integrate with real services)
    async def _fetch_spot_data(self) -> Dict[str, Dict[str, Any]]:
        """Fetch real-time spot data from exchanges via PriceFeedService."""
        try:
            # Fetch multi-asset prices from real exchanges (CoinGecko/CoinCap)
            prices = await self.price_feed.get_multi_asset_prices(["bitcoin", "ethereum", "solana"])

            if not prices:
                logger.warning("Failed to fetch spot prices")
                return {}

            # Format data for arbitrage detector
            formatted_data = {}
            asset_mapping = {
                "bitcoin": "BTC",
                "ethereum": "ETH",
                "solana": "SOL"
            }

            for coin_id, symbol in asset_mapping.items():
                if coin_id in prices:
                    price = prices[coin_id]["usd"]
                    formatted_data[symbol] = {
                        "price": price,
                        "prices": [price] * 10,  # Simplified for now, could fetch historical
                        "volume": prices[coin_id].get("usd_24h_vol", 0)
                    }

            return formatted_data

        except Exception as e:
            logger.error(f"Error fetching spot data: {e}")
            return {}

    async def _fetch_polymarket_data(self) -> Dict[str, Dict[str, Any]]:
        """Fetch Polymarket prediction market data via MarketDiscoveryService."""
        try:
            # Discover and filter markets for BTC, ETH, SOL
            markets = await self.market_discovery.discover_markets()

            if not markets:
                logger.warning("No Polymarket markets found")
                return {}

            # Format data by asset
            formatted_data = {}
            for market in markets:
                asset = market.asset.upper()  # "BTC", "ETH", or "SOL"
                if asset not in formatted_data:
                    formatted_data[asset] = {
                        "price": float(market.yes_price or 0.5),  # Current market price
                        "volume": float(market.volume_24h or 0),
                        "market_id": market.market_id,
                        "liquidity": float(market.liquidity or 0)
                    }

            return formatted_data

        except Exception as e:
            logger.error(f"Error fetching Polymarket data: {e}")
            return {}

    async def _fetch_orderbook(self, market_id: str) -> Optional[OrderbookSnapshot]:
        """Fetch current orderbook from Polymarket."""
        try:
            orderbook = await self.polymarket.get_orderbook(market_id)

            if not orderbook:
                logger.warning(f"Failed to fetch orderbook for {market_id}")
                return None

            return OrderbookSnapshot(
                bids=orderbook.get("bids", []),
                asks=orderbook.get("asks", []),
                timestamp=datetime.now(),
                market_id=market_id
            )

        except Exception as e:
            logger.error(f"Error fetching orderbook for {market_id}: {e}")
            return None

    # Database Persistence Methods
    async def _save_position_to_db(self, position: Position, market_id: str) -> Optional[DBPosition]:
        """Save position to database."""
        try:
            async with self.db_manager.session() as session:
                db_position = DBPosition(
                    market_id=market_id,
                    side=position.side,
                    size=position.size,
                    entry_price=position.entry_price,
                    sentiment_score=position.sentiment_score,
                    confidence=Decimal(str(position.confidence)),
                    is_open=True
                )
                session.add(db_position)
                await session.commit()
                await session.refresh(db_position)
                logger.info(f"Position saved to DB: {db_position.id}")
                return db_position

        except Exception as e:
            logger.error(f"Error saving position to DB: {e}")
            return None

    async def _update_position_in_db(self, position_id: int, current_price: Decimal, is_open: bool = True) -> None:
        """Update position in database with current price."""
        try:
            async with self.db_manager.session() as session:
                result = await session.execute(
                    select(DBPosition).where(DBPosition.id == position_id)
                )
                db_position = result.scalar_one_or_none()

                if db_position:
                    db_position.update_pnl(current_price)
                    db_position.is_open = is_open
                    if not is_open:
                        db_position.closed_at = datetime.now()
                    await session.commit()
                    logger.debug(f"Position {position_id} updated in DB")

        except Exception as e:
            logger.error(f"Error updating position in DB: {e}")

    async def _save_trade_to_db(self, position: Position, market_id: str, exit_price: Decimal, pnl: Decimal) -> Optional[DBTrade]:
        """Save completed trade to database."""
        try:
            async with self.db_manager.session() as session:
                db_trade = DBTrade(
                    market_id=market_id,
                    side=position.side,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    size=position.size,
                    pnl=pnl,
                    strategy="temporal_arbitrage",
                    confidence=Decimal(str(position.confidence))
                )
                session.add(db_trade)
                await session.commit()
                await session.refresh(db_trade)
                logger.info(f"Trade saved to DB: {db_trade.id}, P&L: ${float(pnl):.2f}")
                return db_trade

        except Exception as e:
            logger.error(f"Error saving trade to DB: {e}")
            return None

    async def _get_recent_win_rate(self, num_trades: int = 20) -> float:
        """Get win rate from recent trades in database."""
        try:
            async with self.db_manager.session() as session:
                # Get recent trades
                result = await session.execute(
                    select(DBTrade)
                    .order_by(DBTrade.executed_at.desc())
                    .limit(num_trades)
                )
                recent_trades = result.scalars().all()

                if not recent_trades:
                    return 0.0

                # Calculate win rate
                wins = sum(1 for trade in recent_trades if trade.is_winner())
                win_rate = wins / len(recent_trades)

                logger.debug(f"Recent win rate ({len(recent_trades)} trades): {win_rate:.1%}")
                return win_rate

        except Exception as e:
            logger.error(f"Error calculating recent win rate: {e}")
            return 0.0

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary."""
        strategy_metrics = self.strategy.get_performance_metrics()
        risk_summary = self.risk_manager.get_risk_summary()
        whale_stats = self.whale_detector.get_statistics()
        
        return {
            'bot_stats': self.stats,
            'performance': strategy_metrics,
            'risk': risk_summary,
            'whale': whale_stats,
            'total_pnl': strategy_metrics.get('total_pnl', 0),
            'win_rate': strategy_metrics.get('win_rate', 0),
            'roi_pct': float((strategy_metrics.get('total_pnl', 0) / self.total_capital) * 100) 
        }


async def main():
    """Main entry point."""
    import sys
    
    # Get capital from command line or default
    capital = Decimal(sys.argv[1]) if len(sys.argv) > 1 else Decimal("1000")
    
    # Initialize and start bot
    bot = CashBot(total_capital=capital)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        # Print final summary
        summary = bot.get_performance_summary()
        print("\n" + "="*50)
        print("FINAL PERFORMANCE SUMMARY")
        print("="*50)
        print(f"Total Trades: {summary['bot_stats']['total_trades']}")
        print(f"Win Rate: {summary['win_rate']:.1%}")
        print(f"Total P&L: ${summary['total_pnl']:.2f}")
        print(f"ROI: {summary['roi_pct']:.1f}")
        print(f"Signals Generated: {summary['bot_stats']['signals_generated']}")
        print(f"Signals Executed: {summary['bot_stats']['signals_executed']}")


if __name__ == "__main__":
    asyncio.run(main())
