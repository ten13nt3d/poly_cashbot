#!/bin/bash
# View logs for Polymarket Cash Bot

set -e

# Default to bot logs
SERVICE="${1:-bot}"

echo "📊 Viewing logs for: $SERVICE"
echo "   (Press Ctrl+C to exit)"
echo ""

docker-compose logs -f "$SERVICE"
