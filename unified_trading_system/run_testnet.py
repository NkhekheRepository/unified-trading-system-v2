#!/usr/bin/env python3
"""
Start the trading system with Binance Testnet connection
"""

import asyncio
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)

async def main():
    from continuous_trading_loop import create_testnet_trading_loop, TradingConfig, TradingMode
    from unified_trading_system.observability.alerting import send_system_status_alert
    
    # Create configuration for Binance Testnet
    config = TradingConfig(
        mode=TradingMode.TESTNET,
        symbols=["BTC/USDT", "ETH/USDT"],
        cycle_interval=60.0,  # Run every 60 seconds
        max_position_size=0.1,  # Max 0.1 BTC per trade
        max_daily_loss=10000.0,  # $10,000 max daily loss
        max_orders_per_minute=10,
        enable_alerting=True,
        health_check_port=8080,
    )
    
    # Override signal generator parameters for testing
    config.signal_generator_config = {
        'min_confidence_threshold': 0.3,  # Lowered from 0.85 to 0.3 for testing
        'min_expected_return': 0.001,     # Lowered from 0.005 to 0.001 for testing
        'max_position_size': 0.1,
        'available_capital': 10000.0,     # $10k capital for testing
    }
    
    print("=" * 60)
    print("BINANCE TESTNET TRADING SYSTEM")
    print("=" * 60)
    print(f"Mode: {config.mode.value}")
    print(f"Symbols: {config.symbols}")
    print(f"Cycle Interval: {config.cycle_interval}s")
    print(f"Max Position: {config.max_position_size}")
    print(f"Max Daily Loss: ${config.max_daily_loss}")
    print("=" * 60)
    print("\nStarting trading system...")
    print("Press Ctrl+C to stop\n")
    
    # Create and initialize the trading loop
    from continuous_trading_loop import EnhancedTradingLoop
    loop = EnhancedTradingLoop(config)
    
    try:
        await loop.initialize()
        
        # Send startup alert
        await send_system_status_alert(
            component='trading_loop',
            status='started',
            details={
                'mode': 'BINANCE_TESTNET',
                'symbols': config.symbols,
                'cycle_interval': f'{config.cycle_interval}s'
            }
        )
        
        print("✅ System initialized!")
        print("📊 Health check: http://localhost:8080/health")
        print("📈 Metrics: http://localhost:9090/metrics")
        print("\nTrading started! Press Ctrl+C to stop.\n")
        
        # Start the trading loop
        await loop.start()
        
    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        await loop.shutdown()
        print("\n✅ System shut down gracefully.")

if __name__ == "__main__":
    asyncio.run(main())
