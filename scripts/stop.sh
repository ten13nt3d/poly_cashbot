#!/bin/bash
# Stop the Polymarket Cash Bot

set -e

echo "🛑 Stopping Polymarket Cash Bot..."

docker-compose down

echo "✅ Bot stopped successfully!"
echo ""
echo "💡 To remove all data (⚠️  DESTRUCTIVE):"
echo "   docker-compose down -v"
echo ""
