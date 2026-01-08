#!/bin/bash
# Start the Polymarket Cash Bot using Docker Compose

set -e

echo "🚀 Starting Polymarket Cash Bot..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env file. Please edit it with your API keys!"
        echo "   Then run this script again."
        exit 1
    else
        echo "❌ .env.example not found! Please create .env manually."
        exit 1
    fi
fi

# Build and start services
echo "📦 Building Docker images..."
docker-compose build

echo "🐳 Starting services..."
docker-compose up -d

echo ""
echo "✅ Bot started successfully!"
echo ""
echo "📊 View logs:"
echo "   docker-compose logs -f bot"
echo ""
echo "🛑 Stop bot:"
echo "   docker-compose down"
echo ""
echo "💾 View database:"
echo "   docker-compose exec postgres psql -U cashbot_user -d poly_cashbot"
echo ""
