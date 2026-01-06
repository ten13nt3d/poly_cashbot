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

from src.lib.sentiment.analyzer import HighAccuracySentimentAnalyzer
from src.lib.whale.detector import WhaleDetector, OrderbookSnapshot
from src.lib.strategy.interval_strategy import IntervalStrategy, Position, ExitStrategy
from src.lib.risk.manager import ScalableRiskManager

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
    
    def __init__(self, total_capital: Decimal):
        """Initialize the cash bot with capital."""
        self.total_capital = total_capital
        self.available_capital = total_capital
        
        # Core components
        self.sentiment_analyzer = HighAccuracySentimentAnalyzer()
        self.whale_detector = WhaleDetector("XRP_markets")  
        self.strategy = IntervalStrategy()
        self.risk_manager = ScalableRiskManager(total_capital)
        
        # State tracking
        self.is_running = False
        self.stats = {
            'start_time': None,
            'total_trades': 0,
            'signals_generated': 0,
            'signals_executed': 0
        }
        
        logger.info(
            "Cash bot initialized",
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
        """Analyze markets for trading opportunities."""
        try:
            # Fetch current market data (mock for now)
            market_data = await self._fetch_market_data()
            
            if not market_data:
                return
            
            # Get latest sentiment data
            news_sentiment = await self._fetch_news_sentiment()
            current_volatility = await self._fetch_volatility()
            
            # Analyze for trading signal
            signal = self.sentiment_analyzer.analyze(
                price_data=market_data,
                news_sentiment=news_sentiment,
                current_volatility=current_volatility
            )
            
            self.stats['signals_generated'] += 1
            
            if signal:
                logger.info(
                    f"High-confidence {signal.direction} signal detected",
                    confidence=signal.confidence,
                    sentiment=signal.sentiment_score,
                    reason=signal.reason
                )
                
                # Check if we should trade this signal
                if self.strategy.should_trade(
                    signal_confidence=signal.confidence,
                    sentiment_score=signal.sentiment_score,
                    expected_win_rate=signal.expected_win_rate,
                    market_liquidity=float(market_data.get('volume', [])[-1] if market_data.get('volume') else 10000),
                    capital_available=self.available_capital
                ):
                    # Calculate position size
                    position_size = self.strategy.calculate_position_size(
                        signal.confidence,
                        self.available_capital * Decimal(str(self.risk_manager.params['per_trade_risk']))
                    )
                    
                    # Risk check
                    risk_check = self.risk_manager.validate_order(position_size)
                    if risk_check.passed:
                        # Execute trade
                        await self._execute_trade(signal, position_size)
                    else:
                        logger.info(f"Trade rejected by risk management: {risk_check.reason}")
            else:
                logger.debug("No high-confidence signal detected")
                
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

    async def _execute_front_run(self, alert, position_size: Decimal) -> None:
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
    async def _fetch_market_data(self) -> Optional[Dict[str, Any]]:
        """Fetch current market data."""
        # Mock implementation
        import random
        return {
            'close': [1.0 + random.uniform(-0.01, 0.01) for _ in range(30)],
            'volume': [random.randint(1000, 5000) for _ in range(30)]
        }

    async def _fetch_news_sentiment(self) -> float:
        """Fetch current news sentiment."""
        # Mock implementation - would use real news service
        import random
        return random.uniform(-50, 50)

    async def _fetch_volatility(self) -> float:
        """Fetch current market volatility."""
        # Mock implementation
        return 0.15

    async def _fetch_orderbook(self) -> Optional[OrderbookSnapshot]:
        """Fetch current orderbook."""
        # Mock implementation
        try:
            return OrderbookSnapshot(
                bids=[{'price': 0.55, 'size': 1000}, {'price': 0.54, 'size': 1500}],
                asks=[{'price': 0.56, 'size': 1200}, {'price': 0.57, 'size': 1000}],
                timestamp=datetime.now(),
                market_id="XRP_UP_15min"
            )
        except:
            return None

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
