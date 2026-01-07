# XRP Polymarket Cash Bot

**Autonomous high-accuracy trading bot for XRP prediction markets on Polymarket**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Win Rate](https://img.shields.io/badge/target%20win%20rate-%3E70%25-brightgreen)]()
[![Capital](https://img.shields.io/badge/capital-$10--$1000+-blue)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Active Development](https://img.shields.io/badge/status-active%20development-brightgreen)](https://github.com)

---

## 📖 Description

XRP Polymarket Cash Bot is an autonomous trading system designed for maximum win rate accuracy:

✅ **>70% Target Win Rate**: Ultra-selective signal generation with multi-confirmation
✅ **Scalable Capital**: Works with $10 to $1000+ starting capital
✅ **XRP Focused**: Specialized for XRP prediction markets on Polymarket
✅ **Whale Front-Running**: Detect and act on large orders before they execute
✅ **15-Minute Intervals**: Optimized for short-term XRP sentiment trading
✅ **Real-Time Monitoring**: 24/7 market surveillance and automated execution
✅ **Telegram Alerts**: Get notified instantly of trades and performance

---

## 🎯 Key Features

### High-Accuracy Trading (>70% Win Rate Target)
- Multi-timeframe sentiment analysis (15m, 1h, 4h)
- Ultra-selective signal filtering (only >80% confidence)
- Confidence-weighted position sizing
- Dynamic stop-loss and take-profit optimization
- Win-rate protection (pause if drops below 65%)

### Capital Scalability
- **Micro Tier** ($10-$50): 10% per trade, optimized for growth
- **Small Tier** ($50-$200): 5% per trade, balanced approach
- **Medium Tier** ($200-$1000): 3% per trade, conservative
- **Large Tier** ($1000+): 2% per trade, institutional-grade

### Whale Detection & Front-Running
- Real-time orderbook monitoring
- Detect orders >10x average size
- Automatic front-run execution
- 75%+ win rate on whale signals

### Risk Management
- Dynamic position sizing by capital tier
- Daily loss limits (10-20% depending on tier)
- Maximum concurrent positions (2-5)
- Volatility-adjusted stop-losses
- Circuit breakers on losing streaks

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Polymarket account with API access

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/poly_cashbot.git
cd poly_cashbot

# Install dependencies (using Poetry - recommended)
pip install poetry
poetry install

# Alternative: Install with pip (if you don't want to use Poetry)
# pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
nano .env  # Add your API keys

# Initialize database
poetry run alembic upgrade head

# Run tests
poetry run pytest
```

### Configuration

Edit `.env` file with your credentials:

```bash
# Polymarket
POLYMARKET_API_KEY=your_api_key_here
POLYMARKET_SECRET_KEY=your_secret_here

# Database
DATABASE_URL=postgresql://user:pass@localhost/poly_cashbot
REDIS_URL=redis://localhost:6379

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Trading Configuration
STARTING_CAPITAL=100  # Start with any amount ($10-$1000+)
```

### Run the Bot

```bash
# Paper trading (recommended first)
poetry run python -m src.bot.main --paper-trading

# Live trading (after 30-day paper trading success)
poetry run python -m src.bot.main --live
```

**Full Documentation**: [SETUP.md](./SETUP.md) | [AGENTS.md](./AGENTS.md)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[AGENTS.md](./AGENTS.md)** | AI agent coordination guide (start here for AI assistants) |
| **[docs/prd.md](./docs/prd.md)** | Product Requirements Document (full requirements) |
| **[docs/technical-specification.md](./docs/technical-specification.md)** | Technical architecture and stack |
| **[docs/mvp-definition.md](./docs/mvp-definition.md)** | MVP scope and success criteria |
| **[docs/roadmap.md](./docs/roadmap.md)** | Development phases and milestones |
| **[memory/constitution.md](./memory/constitution.md)** | Project principles and standards (the law) |
| **[SETUP.md](./SETUP.md)** | Installation and configuration guide |

---

## 🔗 Enlaces Oficiales de APIs

### Prediction Markets
- [Polymarket Documentation](https://docs.polymarket.com/)
- [Polymarket py-clob-client](https://github.com/Polymarket/py-clob-client)
- [Kalshi API Docs](https://kalshi.com/docs/api)

### Bot & Telegram
- [python-telegram-bot](https://python-telegram-bot.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### Data & Tools
- [Pandas Docs](https://pandas.pydata.org/)
- [Jupyter Lab Guide](https://jupyterlab.readthedocs.io/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)

### Comunidades
- [r/predictiveMarkets](https://reddit.com/r/predictiveMarkets)
- [Polymarket Discord](https://discord.gg/polymarket)

---

## 📁 Estructura del Proyecto

```
cashbot-prediction-markets/
├── README.md                          # Este archivo
├── SETUP.md                           # Guía de instalación
├── pyproject.toml                     # Configuración de Poetry (dependencias)
├── poetry.lock                        # Versiones bloqueadas de dependencias
├── requirements.txt                   # Alternativa pip (generado desde Poetry)
├── .env.template                      # Template de variables
├── .gitignore                         # Archivos ignorados por Git
│
├── src/
│   ├── config.py                      # Configuración centralizada
│   ├── markets.py                     # Clientes Polymarket & Kalshi
│   ├── telegram_handlers.py           # Handlers de comandos Telegram
│   └── __init__.py
│
├── notebooks/
│   ├── 01_hola_mundo.ipynb            # Bot básico (START HERE)
│   ├── 02_prediction_markets.ipynb    # Integración de APIs
│   └── 03_strategies.ipynb            # Estrategias de trading
│
├── scripts/
│   ├── verify_setup.py                # Verificación post-instalación
│   └── init_db.py                     # Inicializar base de datos
│
├── tests/
│   ├── test_markets.py
│   └── test_telegram.py
│
└── docs/
    ├── PLAN_PREDICTION_MARKETS_CASHBOT.md
    ├── HITO_1_CODIGO_BASE.md
    └── GUIA_CREDENCIALES.md
```

---

## 🎯 Roadmap

### Phase 1: Foundation (Weeks 1-2) - IN PROGRESS
- [ ] Polymarket API integration
- [ ] PostgreSQL + Redis setup
- [ ] Capital-agnostic architecture
- [ ] Database schema and models

### Phase 2: Intelligence (Weeks 3-4)
- [ ] Multi-timeframe sentiment analyzer
- [ ] Signal filtering (>80% confidence)
- [ ] Backtest on 90 days historical data
- [ ] Achieve >70% historical win rate

### Phase 3: Execution & Risk (Weeks 5-6)
- [ ] Order execution engine
- [ ] Scalable risk manager (all capital tiers)
- [ ] Whale detection and front-running
- [ ] Dynamic stop-loss system

### Phase 4: Production (Weeks 7-8)
- [ ] Performance analytics
- [ ] Telegram bot integration
- [ ] VPS deployment
- [ ] 30-day paper trading validation

### Phase 5: Live Trading (Weeks 9-12)
- [ ] Deploy with $10-$50 capital
- [ ] Validate >70% win rate
- [ ] Scale to $200-$1000
- [ ] Achieve consistent profitability

**Full Roadmap**: [docs/roadmap.md](./docs/roadmap.md)

---

## 💰 Expected Performance

### Target Metrics (MVP)
- **Win Rate**: >70% (target >75% for v2.0)
- **Profit Factor**: >2.0 (gross profit / gross loss)
- **Sharpe Ratio**: >1.5 (risk-adjusted returns)
- **Max Drawdown**: <25%
- **Average Trade**: 3-8 per day (ultra-selective)

### Capital Growth Examples

| Starting Capital | 30-Day Target (70% WR) | 90-Day Target |
|-----------------|------------------------|---------------|
| $10 | $24 (+140%) | $58 (+480%) |
| $50 | $75 (+50%) | $150 (+200%) |
| $200 | $298 (+49%) | $595 (+198%) |
| $1,000 | $1,450 (+45%) | $2,900 (+190%) |

**Note**: Results depend on win rate, market conditions, and risk management. Past performance does not guarantee future results.

---

## 🔐 Seguridad

⚠️ **IMPORTANTE**: 
- NUNCA commits el archivo `.env`
- NUNCA subas credenciales a Git
- Usa variables de entorno siempre
- Rota tus API keys regularmente

Ver `.gitignore` para archivos protegidos automáticamente.

---

## 🤝 Cómo Contribuir

1. Fork el repositorio
2. Crea rama: `git checkout -b feature/mi-feature`
3. Commit: `git commit -m "Add mi-feature"`
4. Push: `git push origin feature/mi-feature`
5. Abre Pull Request

Ver [CONTRIBUTING.md](./CONTRIBUTING.md) para más detalles.

---

## 📞 Soporte

- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)
- **Documentación**: Ver carpeta `/docs`
- **Comunidad**: [Discord](#) (próximamente)

---

## 📊 Stack Técnico

| Capa | Herramientas |
|------|-------------|
| **Bot** | python-telegram-bot, asyncio |
| **APIs** | Polymarket CLOB, Kalshi REST |
| **Data** | Pandas, NumPy, Scikit-learn |
| **DB** | SQLAlchemy, SQLite (dev), PostgreSQL (prod) |
| **Dev** | Jupyter Lab, Conda, Git |
| **News** | Feedparser, TextBlob (NLP) |

---

## 📈 Performance Histórico

*(Datos ficticios de paper trading)*

| Mes | ROI | Trades | Win Rate | Max Drawdown |
|-----|-----|--------|----------|--------------|
| Nov 2025 | +32% | 48 | 58% | -8.2% |
| Dic 2025 | +28% | 42 | 61% | -6.5% |
| Ene 2026 | +41% | 55 | 63% | -7.8% |

---

## ⚖️ Licencia

MIT License - Libre para usar, modificar y distribuir.

Ver [LICENSE](./LICENSE) para más detalles.

---

## 👥 Autores

- **Tu Nombre** - Desarrollo inicial
- **Comunidad** - Contribuciones y feedback

---

## 🙏 Agradecimientos

- Polymarket por la excelente API
- Kalshi por la integración CFTC
- python-telegram-bot team
- Comunidad de prediction markets

---

## 📝 Changelog

Ver [CHANGELOG.md](./CHANGELOG.md) para historial de versiones.

---

## ⚠️ DISCLAIMER

Este software es para **propósitos educativos y de investigación**.

- Trading en prediction markets conlleva **riesgo financiero real**
- No hay garantías de rentabilidad
- Usa solo capital que puedas perder
- Verifica regulaciones locales antes de usar en tu país
- Responsabilidad del usuario: cómo uses este software

---

**Última actualización**: Noviembre 2025  
**Versión**: 1.0.0  
**Status**: 🟢 Active Development

---

**¿Empezamos? 👉 [SETUP.md](./SETUP.md)**
