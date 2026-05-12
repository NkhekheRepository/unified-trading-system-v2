#!/usr/bin/env python3
"""
Start the ENHANCED trading system with all upgrades on Binance Testnet
Version 2.0 - With Enhanced Exit Strategy & Dynamic Risk Management
"""

import asyncio
import os
import logging

# Load API keys from .env (only for run_enhanced_testnet.py)
from dotenv import load_dotenv
load_dotenv('/home/nkhekhe/unified_trading_system/.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)

async def main():
    from continuous_trading_loop_binance import EnhancedTradingLoop, TradingConfig, TradingMode
    from observability.alerting import send_system_status_alert
    
    # Create configuration for Binance Testnet
    config = TradingConfig(
        mode=TradingMode.TESTNET,
        symbols=[
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", 
            "ADA/USDT", "XRP/USDT", "DOGE/USDT", "DOT/USDT",
            "AVAX/USDT", "LINK/USDT", "LTC/USDT", "BCH/USDT"
        ],
        cycle_interval=10.0,  # Run every 10 seconds for faster trading
        max_position_size=0.1,
        max_daily_loss=10000.0,
        max_orders_per_minute=20,
        enable_alerting=True,
        health_check_port=8080,
    )
    
    print("=" * 70)
    print("🚀 ENHANCED TRADING SYSTEM v2.0 - BINANCE TESTNET")
    print("=" * 70)
    print("Features:")
    print("  ✓ Regime-aware time exit (30-90s)")
    print("  ✓ Volatility-adjusted stop-loss (1.5%-3%)")
    print("  ✓ 3-tier take-profit system (1.5%, 3%, 5%)")
    print("  ✓ Trailing stop (activates at 2% profit)")
    print("  ✓ Dynamic position sizing (confidence-based)")
    print("  ✓ Regime risk modifiers (0.3x-1.2x)")
    print("  ✓ Hourly risk modifiers (0.3x-1.3x)")
    print("  ✓ Streak-based risk adjustment")
    print("=" * 70)
    print(f"Mode: {config.mode.value}")
    print(f"Symbols: {len(config.symbols)} trading pairs")
    print(f"Cycle Interval: {config.cycle_interval}s")
    print(f"Max Position: {config.max_position_size}")
    print("=" * 70)
    print("\nStarting enhanced trading system...")
    print("Press Ctrl+C to stop\n")
    
    # Create and initialize the enhanced trading loop
    loop = EnhancedTradingLoop(config)
    
    try:
        await loop.initialize()
        
        # Send startup alert
        await send_system_status_alert(
            component='trading_loop',
            status='started',
            details={
                'mode': 'BINANCE_TESTNET_ENHANCED_V2',
                'symbols': config.symbols,
                'cycle_interval': f'{config.cycle_interval}s',
                'features': ['regime_exit', 'dynamic_sl', '3tier_tp', 'trailing_stop', 'dynamic_risk']
            }
        )
        
        print("✅ Enhanced System initialized!")
        print("📊 Health check: http://localhost:8080/health")
        print("📈 Metrics: http://localhost:9090/metrics")
        print("\n🚀 Trading started! Press Ctrl+C to stop.\n")
        
        # Start the trading loop
        await loop.start()
        
    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await loop.shutdown()
        print("\n✅ System shut down gracefully.")

if __name__ == "__main__":
    asyncio.run(main())