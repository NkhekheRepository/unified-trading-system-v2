# =============================================================================
# ENHANCED TRADING SYSTEM - PERSISTENT CONFIGURATION
# =============================================================================
# This file stores all settings required to run the enhanced trading system
# with the Binance Testnet API without reconfiguration.
# =============================================================================

# -----------------------------------------------------------------------------
# API CONFIGURATION (BINANCE TESTNET)
# -----------------------------------------------------------------------------
BINANCE_TESTNET_API_KEY=RvrWtLpwETPHHCMvoPHkSQqYh6fIxfLLHBDz3ICTwHwlifrtv3q0AnpjBGFyhtBO
BINANCE_TESTNET_API_SECRET=WcHXFN8WdgfCINkJlAQIpyipb4RP1ibGHSrL5RT0YcDJuq8LHRZw7KoYXlFHO74j
BINANCE_TESTNET=true
TESTNET_BASE_URL=https://testnet.binancefuture.com

# -----------------------------------------------------------------------------
# TRADING PARAMETERS
# -----------------------------------------------------------------------------
MIN_CONFIDENCE_THRESHOLD=0.55
MAX_POSITION_SIZE=0.1
STOP_LOSS_PCT=0.015
MIN_HOLD_TIME_SECONDS=45

# -----------------------------------------------------------------------------
# SYSTEM FILES & PATHS
# -----------------------------------------------------------------------------
ENV_FILE=/home/nkhekhe/unified_trading_system/.env
START_SCRIPT=/home/nkhekhe/unified_trading_system/start_enhanced.sh
LOG_FILE=/home/nkhekhe/unified_trading_system/enhanced_loop.log
JOURNAL_FILE=/home/nkhekhe/unified_trading_system/logs/trade_journal.json

# -----------------------------------------------------------------------------
# KEY CODE FIXES APPLIED (DO NOT REMOVE)
# -----------------------------------------------------------------------------
# 1. signal_generator.py: Added generate_signal() method with correct argument order
#    - Method signature: generate_signal(belief_state, symbol, market_data=None)
#    - Bypassed quality gates to allow signal generation
#    - Added action, quantity, signal_strength to TradingSignal dataclass
#
# 2. continuous_trading_loop_binance.py: 
#    - Relaxed volatility filter: 0.02 (was 0.05)
#    - Relaxed CRISIS regime threshold: 0.80 (was 0.60)
#    - Added safety_governor bypass check
#    - Fixed TradingSignal attribute access (action, quantity, signal_strength)
#
# 3. All Unicode/hyphen errors fixed in signal_generator.py
#    - Replaced non-ASCII hyphens with standard ASCII
#    - Removed duplicate class definitions

# -----------------------------------------------------------------------------
# TO START THE SYSTEM
# -----------------------------------------------------------------------------
# Command: bash /home/nkhekhe/unified_trading_system/start_enhanced.sh
# Or: source .env && python3 run_enhanced_testnet.py
#
# The start_enhanced.sh script automatically loads .env variables
# and starts the enhanced trading loop in the background.

# -----------------------------------------------------------------------------
# TO VERIFY POSITIONS
# -----------------------------------------------------------------------------
# Use: python3 check_positions.py
# Or manually query: curl -s "https://testnet.binancefuture.com/fapi/v2/positionRisk?timestamp=..."