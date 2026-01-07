"""Market discovery service with filtering and database persistence."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from ..config import settings
from ..database import DatabaseManager
from ..models import Market
from .logging_config import get_logger
from .polymarket import PolymarketClient
from .price_feed import PriceFeedService

logger = get_logger(__name__)


class MarketDiscoveryService:
    """
    Market discovery and filtering service.

    Discovers markets from Polymarket, filters by criteria, and persists to database.

    Filtering criteria:
    - Asset: XRP > BTC > ETH (priority order)
    - Liquidity: >= $10,000
    - Time window: 15 minutes < expiration < 24 hours
    - Active markets only

    Example:
        service = MarketDiscoveryService(
            polymarket_client,
            price_feed,
            db_manager
        )
        markets = await service.discover_markets()
    """

    def __init__(
        self,
        polymarket_client: PolymarketClient,
        price_feed: PriceFeedService,
        db_manager: DatabaseManager,
    ):
        """
        Initialize market discovery service.

        Args:
            polymarket_client: Polymarket API client
            price_feed: Price feed service
            db_manager: Database manager
        """
        self.polymarket = polymarket_client
        self.price_feed = price_feed
        self.db = db_manager

        logger.info("market_discovery_service_initialized")

    def _detect_asset(self, market: dict) -> Optional[str]:
        """
        Detect related crypto asset from market question.

        Args:
            market: Market dictionary with question field

        Returns:
            Asset symbol (XRP, BTC, ETH) or None if not detected

        Priority order: XRP > BTC > ETH
        """
        question = market.get("question", "").upper()

        # Priority order matters!
        if "XRP" in question or "RIPPLE" in question:
            return "XRP"
        elif "BTC" in question or "BITCOIN" in question:
            return "BTC"
        elif "ETH" in question or "ETHEREUM" in question:
            return "ETH"

        return None

    def _is_time_valid(self, market: dict) -> bool:
        """
        Check if market expiration is in valid time window.

        Args:
            market: Market dictionary with end_date field

        Returns:
            True if 15 minutes < time_until_expiry < 24 hours
        """
        try:
            now = datetime.now(timezone.utc)
            end_date_str = market.get("end_date")

            if not end_date_str:
                return False

            # Parse end date (handle both with and without timezone)
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

            time_until = end_date - now

            # Must be between 15 minutes and 24 hours
            min_time = timedelta(minutes=15)
            max_time = timedelta(hours=24)

            return min_time <= time_until <= max_time

        except Exception as e:
            logger.warning(
                f"Time validation failed for market {market.get('id')}: {str(e)}"
            )
            return False

    def _sort_by_priority(self, markets: list[dict]) -> list[dict]:
        """
        Sort markets by asset priority (XRP > BTC > ETH).

        Args:
            markets: List of market dictionaries

        Returns:
            Sorted list with XRP markets first
        """
        priority_map = {"XRP": 3, "BTC": 2, "ETH": 1, None: 0}

        return sorted(
            markets,
            key=lambda m: priority_map.get(m.get("related_asset"), 0),
            reverse=True,
        )

    def _filter_markets(self, raw_markets: list[dict]) -> list[dict]:
        """
        Apply all filters to raw market data.

        Filters:
        1. Asset detection (XRP/BTC/ETH only)
        2. Liquidity (>= min_market_liquidity from settings)
        3. Time window (15min - 24hr)
        4. Priority sort (XRP > BTC > ETH)

        Args:
            raw_markets: List of raw market dictionaries from API

        Returns:
            Filtered and sorted list of markets
        """
        filtered = []

        for market in raw_markets:
            # Detect asset
            asset = self._detect_asset(market)
            if asset is None:
                continue

            market["related_asset"] = asset

            # Check liquidity
            liquidity = Decimal(str(market.get("liquidity", 0)))
            if liquidity < settings.min_market_liquidity:
                logger.debug(
                    f"Market filtered (liquidity) - ID: {market.get('id')}, "
                    f"Liquidity: ${liquidity}, Threshold: ${settings.min_market_liquidity}"
                )
                continue

            # Check time window
            if not self._is_time_valid(market):
                logger.debug(f"Market filtered (time) - ID: {market.get('id')}")
                continue

            filtered.append(market)

        # Sort by priority
        filtered = self._sort_by_priority(filtered)

        logger.info(
            f"Markets filtered - Total: {len(raw_markets)}, Filtered: {len(filtered)}"
        )

        return filtered

    async def _save_markets(self, markets: list[dict]) -> list[Market]:
        """
        Save filtered markets to database with upsert pattern.

        Args:
            markets: List of filtered market dictionaries

        Returns:
            List of Market model instances

        Note:
            Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE for idempotency
        """
        async with self.db.session() as session:
            saved_markets = []

            for market_data in markets:
                # Parse end date
                end_date_str = market_data.get("end_date")
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)

                # Upsert statement
                stmt = insert(Market).values(
                    id=market_data["id"],
                    question=market_data["question"],
                    end_date=end_date,
                    yes_price=Decimal(str(market_data.get("yes_price", "0"))),
                    no_price=Decimal(str(market_data.get("no_price", "0"))),
                    volume_24h=Decimal(str(market_data.get("volume_24h", "0"))),
                    liquidity=Decimal(str(market_data.get("liquidity", "0"))),
                    related_asset=market_data.get("related_asset"),
                )

                # On conflict, update prices and metrics
                stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "yes_price": stmt.excluded.yes_price,
                        "no_price": stmt.excluded.no_price,
                        "volume_24h": stmt.excluded.volume_24h,
                        "liquidity": stmt.excluded.liquidity,
                        "updated_at": datetime.now(timezone.utc),
                    },
                )

                await session.execute(stmt)

            # Commit all upserts
            await session.commit()

            # Retrieve saved markets
            for market_data in markets:
                result = await session.execute(
                    select(Market).where(Market.id == market_data["id"])
                )
                market = result.scalar_one_or_none()
                if market:
                    saved_markets.append(market)

            logger.info(
                "markets_saved",
                count=len(saved_markets),
            )

            return saved_markets

    async def discover_markets(self) -> list[Market]:
        """
        Discover, filter, and save markets from Polymarket.

        Flow:
        1. Fetch all markets from Polymarket API
        2. Filter by asset, liquidity, and time window
        3. Sort by priority (XRP > BTC > ETH)
        4. Save to database (upsert pattern)

        Returns:
            List of Market model instances that passed filters

        Example:
            markets = await service.discover_markets()
            for market in markets:
                print(f"{market.related_asset}: {market.question}")
        """
        logger.info("Discovering markets")

        # Fetch from Polymarket
        raw_markets = await self.polymarket.get_markets()

        logger.info(f"Markets fetched - Count: {len(raw_markets)}")

        # Filter markets
        filtered_markets = self._filter_markets(raw_markets)

        # Save to database
        saved_markets = await self._save_markets(filtered_markets)

        logger.info(
            f"Discovery complete - Total fetched: {len(raw_markets)}, "
            f"Filtered: {len(filtered_markets)}, Saved: {len(saved_markets)}"
        )

        return saved_markets

    async def update_market_prices(self, market_id: str) -> Optional[Market]:
        """
        Update market prices from orderbook.

        Args:
            market_id: Market identifier

        Returns:
            Updated Market instance or None if not found

        Example:
            market = await service.update_market_prices("0x123abc...")
        """
        try:
            # Fetch orderbook
            orderbook = await self.polymarket.get_order_book(market_id)

            # Calculate mid prices from orderbook
            # Note: Actual implementation depends on orderbook structure
            # This is a simplified version
            yes_price = Decimal(str(orderbook.get("yes_price", "0")))
            no_price = Decimal(str(orderbook.get("no_price", "0")))
            volume_24h = Decimal(str(orderbook.get("volume_24h", "0")))
            liquidity = Decimal(str(orderbook.get("liquidity", "0")))

            # Update in database
            async with self.db.session() as session:
                result = await session.execute(
                    select(Market).where(Market.id == market_id)
                )
                market = result.scalar_one_or_none()

                if market:
                    market.yes_price = yes_price
                    market.no_price = no_price
                    market.volume_24h = volume_24h
                    market.liquidity = liquidity

                    await session.commit()

                    logger.info(
                        f"Market prices updated - ID: {market_id}, "
                        f"Yes: {yes_price}, No: {no_price}"
                    )

                    return market

        except Exception as e:
            logger.error(
                f"Update market prices failed for {market_id} - "
                f"{type(e).__name__}: {str(e)}"
            )

        return None
