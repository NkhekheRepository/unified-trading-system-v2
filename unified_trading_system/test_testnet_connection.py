import pytest

# Skip this test suite if the Binance futures client library is unavailable.
pytest.importorskip("binance", reason="Binance client not available")
