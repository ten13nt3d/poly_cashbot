#!/usr/bin/env python3

from src.lib.whale.detector import WhaleDetector, OrderbookSnapshot
from decimal import Decimal
from datetime import datetime
import time

# Create detector
detector = WhaleDetector('XRP_UP_market_12345')

# Add some historical order sizes first (smaller orders to establish baseline)
for i in range(20):
    small_snapshot = OrderbookSnapshot(
        bids=[{'price': 0.55, 'size': 1200 + i}, {'price': 0.54, 'size': 1000}],  # Normal sizes
        asks=[{'price': 0.56, 'size': 1100}, {'price': 0.57, 'size': 900}],
        timestamp=datetime.now(),
        market_id='XRP_UP_market_12345'
    )
    detector.update_orderbook_snapshot(small_snapshot)

# Now create orderbook with a large whale order (>$10k)
orderbook = OrderbookSnapshot(
    bids=[{'price': 0.55, 'size': 25000}, {'price': 0.54, 'size': 18000}],  # Large buy orders
    asks=[{'price': 0.56, 'size': 15000}, {'price': 0.57, 'size': 12000}],
    timestamp=datetime.now(),
    market_id='XRP_UP_market_12345'
)

# Update orderbook and get alerts
alerts = detector.update_orderbook_snapshot(orderbook)

print(f'Whale alerts detected: {len(alerts)}')
for alert in alerts:
    print(f'- {alert.side.upper()} order: ${alert.order_size:,.2f}')
    print(f'  Relative size: {alert.relative_size:.1f}x average')
    print(f'  Expected impact: {alert.expected_impact:.1%}')
    print(f'  Confidence: {alert.confidence:.1%}')
    print(f'  Minimum position: ${detector.calculate_front_run_position_size(alert, Decimal("1000")):,.2f}')
