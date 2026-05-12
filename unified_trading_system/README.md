# Unified Trading System

**POMDP-based autonomous Binance Futures trading system with regime detection, Kelly position sizing, and full observability.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 28/28](https://img.shields.io/badge/tests-28/28-brightgreen.svg)](tests/test_signal_quality.py)
[![Binance Testnet](https://img.shields.io/badge/binance-testnet-orange.svg)](https://testnet.binancefuture.com/)

---

```bash
git clone <repo-url> && cd unified_trading_system
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit with your Testnet API keys
python3 run_enhanced_testnet.py
```

---

**Full documentation:** [`DOCUMENTATION.md`](DOCUMENTATION.md) — architecture, module reference, trading logic, configuration, tests, infrastructure, troubleshooting.

---

### Quick Reference

| Task | Command |
|------|---------|
| Run testnet | `python3 run_enhanced_testnet.py` |
| Run live | `python3 run_enhanced_live.py` |
| Run tests | `python3 -m pytest tests/test_signal_quality.py -v` |
| Health check | `curl http://localhost:8080/health` |
| Check logs | `tail -f logs/testnet/output.log` |

---

### Recent Fixes (May 2026)

- **Dead code fix**: Health server initialization was trapped in unreachable code inside `_get_account_balance`. Now runs properly in `initialize()`.
- **Test fixes**: 3 tests fixed (2x signature mismatch, 1x bound adjustment). All 28 pass.
- **Security**: Real credential placeholders sanitized from repo.
- **Doc**: Comprehensive `DOCUMENTATION.md` replaces 15 fragmented docs.
