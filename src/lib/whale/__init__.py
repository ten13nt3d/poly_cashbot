"""Whale detection and front-running module."""

from .detector import WhaleDetector, WhaleAlert, OrderbookSnapshot

__all__ = ["WhaleDetector", "WhaleAlert", "OrderbookSnapshot"]
