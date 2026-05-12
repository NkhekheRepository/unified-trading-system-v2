#!/usr/bin/env python3
"""Startup script for the enhanced trading system"""
import sys
import os

# Ensure we're in the right directory
os.chdir('/home/nkhekhe/unified_trading_system')

# Load API keys from .env
from dotenv import load_dotenv
load_dotenv('/home/nkhekhe/unified_trading_system/.env')

# Import and run
from continuous_trading_loop_binance import EnhancedTradingLoop, TradingConfig, TradingMode
import asyncio

async def main():
    config = TradingConfig(
        mode=TradingMode.TESTNET,
        symbols=[
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", 
            "ADA/USDT", "XRP/USDT", "DOGE/USDT", "DOT/USDT",
            "AVAX/USDT", "LINK/USDT", "LTC/USDT", "BCH/USDT"
        ],
        cycle_interval=10.0,
        max_position_size=0.1,
        max_daily_loss=10000.0,
        max_orders_per_minute=20,
        enable_alerting=True,
        health_check_port=8080,
    )
    
    loop = EnhancedTradingLoop(config)
    
    try:
        await loop.initialize()
        print("✅ System initialized, starting trading loop...")
        await loop.start()
    except KeyboardInterrupt:
        print("Shutdown requested...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await loop.shutdown()
        print("System shut down.")

if __name__ == "__main__":
    asyncio.run(main())
