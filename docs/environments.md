# Environments
# Local vs VPS Deployment Guide

**Purpose**: Document how to run the bot locally for testing and on a VPS for 24/7 operation, including rough cost expectations.

---

## Local Environment (Development/Testing)

**Use Case**: Rapid iteration, paper trading, strategy tuning, and manual validation.

**Recommended Setup**:
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- `.env` for local secrets (never commit)

**Notes**:
- CLI + Telegram only (no web UI in MVP).
- Prefer Docker Compose for consistent local services.
- Use paper trading or sandbox keys by default.

**Estimated Cost**: $0 (local machine), plus optional API costs.

---

## VPS Environment (24/7 Operation)

**Use Case**: Continuous operation without relying on a personal machine.

**Recommended Setup**:
- Ubuntu LTS VPS
- 1-2 vCPU, 2-4GB RAM, 25-50GB SSD
- PostgreSQL + Redis on the same box for MVP
- systemd service for auto-restart

**Notes**:
- Run with production API keys.
- Enable basic monitoring + daily backups.
- Keep a rollback plan (previous container or git revision).

**Estimated Cost**:
- Low tier: $5-$10/month (testing with small capital)
- Standard: $15-$25/month (recommended for stable 24/7)

---

## Promotion Path (Local -> VPS)

1. Validate strategy locally (paper trading).
2. Deploy to VPS with small capital ($10-$50).
3. Monitor win rate and stability for 2-4 weeks.
4. Scale capital gradually up to $1000+.

---

## Environment Constraints

- No scraping web pages; only official APIs.
- MVP remains CLI + Telegram only.
- UI/UX work (Polyglobe-inspired) is planned for V3/V4.
