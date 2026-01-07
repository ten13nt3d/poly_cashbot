# 🚀 SETUP GUIDE - CashBot Prediction Markets

**Para desarrolladores que clonan este repositorio por primera vez.**

---

## 📋 PREREQUISITOS

### Sistema Operativo
- Linux (Ubuntu 20.04+) ✅
- macOS (10.14+)
- Windows 10+ (con WSL2)

### Herramientas Requeridas

| Herramienta | Versión | Enlace | Propósito |
|------------|---------|--------|----------|
| **Conda** | 24.0+ | [Instalar Miniconda](https://docs.conda.io/projects/miniconda/en/latest/miniconda-install.html) | Gestión de entornos Python |
| **Git** | 2.30+ | [Instalar Git](https://git-scm.com/downloads) | Control de versiones |
| **Python** | 3.11+ | Incluido en Conda | Lenguaje principal |
| **Jupyter Lab** | 4.0+ | Se instala con Conda | IDE interactivo |

---

## 🔧 INSTALACIÓN RÁPIDA (5 min)

### 1. Clonar el Repositorio

```bash
git clone https://github.com/TuUsuario/cashbot-prediction-markets.git
cd cashbot-prediction-markets
```

### 2. Crear Entorno Conda

```bash
# Crear entorno con Python 3.11
conda env create -f environment.yml

# O manualmente:
conda create -n cashbot python=3.11 -y
conda activate cashbot
```

### 3. Instalar Dependencias

**Opción A: Usando Poetry (Recomendado)**
```bash
# Instalar Poetry si no lo tienes
pip install poetry

# Instalar todas las dependencias
poetry install
```

**Opción B: Usando pip**
```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

```bash
# Copiar template
cp .env.template .env

# Editar con tus credenciales
nano .env

# Mínimo necesario:
# - TELEGRAM_BOT_TOKEN
# - POLYMARKET_API_KEY
# - KALSHI_API_KEY
```

📍 **[Cómo obtener credenciales](./docs/GUIA_CREDENCIALES.md)**

### 5. Verificar Setup

```bash
python scripts/verify_setup.py
```

Deberías ver:
```
✅ Python 3.11+
✅ Todas las dependencias instaladas
✅ .env configurado
✅ Jupyter Lab disponible
```

### 6. Iniciar Jupyter Lab

```bash
conda activate cashbot
jupyter lab
```

Se abrirá en `http://localhost:8888`

---

## 📁 ESTRUCTURA DEL PROYECTO

```
cashbot-prediction-markets/
├── pyproject.toml               # Configuración de Poetry (dependencias)
├── poetry.lock                  # Versiones bloqueadas de dependencias
├── requirements.txt             # Alternativa para pip (generado desde Poetry)
├── .env.template               # Template de variables
├── .gitignore                  # Archivos ignorados
│
├── src/
│   ├── __init__.py
│   ├── config.py               # Configuración centralizada
│   ├── markets.py              # Clientes API
│   └── telegram_handlers.py    # Handlers Telegram
│
├── notebooks/
│   ├── 01_hola_mundo.ipynb     # Bot básico funcional
│   ├── 02_prediction_markets.ipynb
│   └── 03_strategies.ipynb
│
├── scripts/
│   ├── verify_setup.py         # Verificación setup
│   └── init_db.py              # Inicializar BD
│
├── tests/
│   └── test_markets.py         # Tests unitarios
│
└── docs/
    ├── PLAN_PREDICTION_MARKETS_CASHBOT.md
    ├── HITO_1_CODIGO_BASE.md
    └── GUIA_CREDENCIALES.md
```

---

## 🔗 DOCUMENTACIÓN OFICIAL

### Python & Conda
- [Conda Documentation](https://docs.conda.io/)
- [Python 3.11 Docs](https://docs.python.org/3.11/)
- [Virtual Environments Best Practices](https://docs.python.org/3.11/tutorial/venv.html)

### Telegram Bot
- [python-telegram-bot Docs](https://python-telegram-bot.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### Prediction Markets
- [Polymarket Documentation](https://docs.polymarket.com/)
- [Polymarket py-clob-client GitHub](https://github.com/Polymarket/py-clob-client)
- [Kalshi API Docs](https://kalshi.com/docs/api)
- [FinFeedAPI (Agregador)](https://finfeedapi.com/)

### Data & Analysis
- [Pandas Tutorial](https://pandas.pydata.org/docs/getting_started/intro_tutorials/index.html)
- [Scikit-learn Guide](https://scikit-learn.org/stable/modules/preprocessing.html)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/20/orm/quickstart.html)

### Jupyter
- [Jupyter Lab User Guide](https://jupyterlab.readthedocs.io/en/stable/user_guide.html)
- [Jupyter Notebook Shortcuts](https://jupyterlab.readthedocs.io/en/stable/user_guide.html#keyboard-shortcuts)

---

## 📦 DEPENDENCIAS PRINCIPALES

### Backend Telegram
```yaml
python-telegram-bot: 20.7     # Bot framework
python-dotenv: 1.0.0          # Variables de entorno
aiohttp: 3.9.0                # Async HTTP
websockets: 12.0              # WebSocket support
```

### Prediction Markets APIs
```yaml
polymarket-py-client: 0.2.0   # Polymarket CLOB
requests: 2.31.0              # HTTP requests
```

### Data & Analysis
```yaml
pandas: 2.1.0                 # Manipulación de datos
numpy: 1.24.0                 # Cálculos numéricos
scikit-learn: 1.3.0           # Machine Learning
textblob: 0.17.1              # Sentiment Analysis
feedparser: 6.0.10            # RSS feeds
```

### Database
```yaml
sqlalchemy: 2.0.0             # ORM
sqlite3: (built-in)           # Dev DB
psycopg2-binary: 2.9.0        # PostgreSQL (prod)
```

**Ver archivo completo**: [`requirements.txt`](./requirements.txt)

---

## 🐍 CONDA CHEAT SHEET

```bash
# Activar entorno
conda activate cashbot

# Desactivar
conda deactivate

# Ver entornos disponibles
conda env list

# Actualizar entorno desde archivo
conda env update -f environment.yml --prune

# Limpiar caché (libera espacio)
conda clean --all

# Reinstalar todo limpio
conda env remove -n cashbot
conda env create -f environment.yml
```

**Más**: [Conda Cheat Sheet](https://docs.conda.io/projects/conda/en/latest/user-guide/cheatsheet.html)

---

## 🧪 VERIFICACIÓN POST-INSTALACIÓN

### 1. Verificar Python
```bash
python --version
# Debería mostrar: Python 3.11.x
```

### 2. Verificar Jupyter
```bash
jupyter --version
# Debería mostrar: 4.0.x o superior
```

### 3. Verificar Importaciones
```bash
python -c "import telegram; import pandas; import requests; print('✅ All imports OK')"
```

### 4. Verificar .env
```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('✅ .env loaded')"
```

### 5. Test Script Completo
```bash
python scripts/verify_setup.py
```

---

## 🚦 TROUBLESHOOTING

### "conda: command not found"
→ [Reinstalar Miniconda](https://docs.conda.io/projects/miniconda/en/latest/miniconda-install.html)

### "ModuleNotFoundError: No module named 'telegram'"
```bash
conda activate cashbot
pip install python-telegram-bot
```

### "No such file or directory: '.env'"
```bash
cp .env.template .env
# Luego edita con tus credenciales
```

### Jupyter no inicia
```bash
conda deactivate
conda activate cashbot
jupyter lab --ip=0.0.0.0 --no-browser
```

### "SSL certificate_verify_failed"
```bash
# Linux
pip install --upgrade certifi

# macOS
/Applications/Python\ 3.11/Install\ Certificates.command
```

**Más troubleshooting**: [Conda FAQ](https://docs.conda.io/projects/conda/en/latest/user-guide/troubleshooting.html)

---

## 📚 PRÓXIMOS PASOS

1. ✅ Completar setup (has llegado aquí)
2. 📖 Leer: [`docs/PLAN_PREDICTION_MARKETS_CASHBOT.md`](./docs/PLAN_PREDICTION_MARKETS_CASHBOT.md)
3. 🔑 Obtener credenciales: [`docs/GUIA_CREDENCIALES.md`](./docs/GUIA_CREDENCIALES.md)
4. 💻 Ejecutar: `notebooks/01_hola_mundo.ipynb`
5. 🤖 Comenzar Hito 1: [`docs/HITO_1_CODIGO_BASE.md`](./docs/HITO_1_CODIGO_BASE.md)

---

## 🤝 CONTRIBUIR

1. Fork el repositorio
2. Crea rama: `git checkout -b feature/mi-feature`
3. Commit: `git commit -m "Add mi-feature"`
4. Push: `git push origin feature/mi-feature`
5. Abre Pull Request

**Conventions**: [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 📞 SOPORTE

- **Issues**: [GitHub Issues](../../issues)
- **Docs**: [`/docs`](./docs/)
- **Comunidad**: [Discord](#)

---

## ⚖️ LICENCIA

MIT License - Ver [`LICENSE`](./LICENSE)

---

**Última actualización**: Noviembre 2025  
**Version**: 1.0.0  
**Python**: 3.11+  
**Maintainer**: [@tuusername](https://github.com/tuusername)
