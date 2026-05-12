import asyncio
import json
import logging
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
import websockets
import aiohttp
from dataclasses import dataclass, asdict
import pickle
import mmap
import signal

try:
    import posix_ipc
    HAS_POSIX_IPC = True
except ImportError:
    HAS_POSIX_IPC = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not HAS_POSIX_IPC:
    logger.warning("posix_ipc not available, using fallback pipeline")

@dataclass
class MarketDataTick:
    """Lightweight market data tick for zero-copy transfer"""
    symbol: str
    price: float
    bid: float
    ask: float
    volume: float
    timestamp: float
    order_book_imbalance: float
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for zero-copy transfer"""
        return pickle.dumps(asdict(self))
    
    @staticmethod
    def from_bytes(data: bytes) -> 'MarketDataTick':
        """Deserialize from bytes"""
        d = pickle.loads(data)
        return MarketDataTick(**d)

class AsyncWebSocketManager:
    """Async WebSocket manager for real-time market data"""
    
    def __init__(self, symbols: List[str], buffer_size: int = 10000):
        self.symbols = symbols
        self.ws_url = "wss://stream.binance.com:9443/ws"
        self.connections = {}
        self.callbacks = []
        self.running = False
        self.data_buffer = asyncio.Queue(maxsize=buffer_size)
        self.reconnect_delay = 1.0
        
    def add_callback(self, callback: Callable[[MarketDataTick], None]):
        """Add callback for processing ticks"""
        self.callbacks.append(callback)
        
    async def connect_symbol(self, symbol: str):
        """Connect to WebSocket for a symbol"""
        stream_name = f"{symbol.lower()}@trade"
        url = f"{self.ws_url}/{stream_name}"
        
        while self.running:
            try:
                async with websockets.connect(url) as ws:
                    logger.info(f"Connected to {symbol} stream")
                    async for message in ws:
                        if not self.running:
                            break
                        data = json.loads(message)
                        tick = self._parse_trade_data(symbol, data)
                        if tick:
                            await self.data_buffer.put(tick)
                            for cb in self.callbacks:
                                cb(tick)
            except Exception as e:
                logger.error(f"WebSocket error for {symbol}: {e}")
                if self.running:
                    await asyncio.sleep(self.reconnect_delay)
                    self.reconnect_delay = min(self.reconnect_delay * 2, 30.0)
    
    def _parse_trade_data(self, symbol: str, data: Dict) -> Optional[MarketDataTick]:
        """Parse trade data from WebSocket"""
        try:
            return MarketDataTick(
                symbol=symbol,
                price=float(data.get('p', 0)),
                bid=0.0,
                ask=0.0,
                volume=float(data.get('q', 0)),
                timestamp=float(data.get('T', datetime.now().timestamp() * 1000)) / 1000.0,
                order_book_imbalance=0.0
            )
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None
    
    async def start(self):
        """Start all WebSocket connections"""
        self.running = True
        self.reconnect_delay = 1.0
        
        tasks = []
        for symbol in self.symbols:
            task = asyncio.create_task(self.connect_symbol(symbol))
            tasks.append(task)
        
        logger.info(f"Started async data feed for {len(self.symbols)} symbols")
        await asyncio.gather(*tasks)
    
    async def stop(self):
        """Stop all connections"""
        self.running = False
        logger.info("Stopped async data feed")

class ZeroCopyPipeline:
    """Zero-copy data pipeline using shared memory for inter-module communication"""
    
    def __init__(self, name: str = "trading_pipeline", size: int = 1024 * 1024):
        self.name = name
        self.size = size
        self.memory = None
        self.shm = None
        self.use_fallback = not HAS_POSIX_IPC
        self.fallback_buffer = {}
        
    def initialize(self):
        """Initialize shared memory segment"""
        if self.use_fallback:
            logger.info("Using fallback pipeline (no posix_ipc)")
            return True
        
        try:
            self.shm = posix_ipc.SharedMemory(
                name=self.name,
                flags=posix_ipc.O_CREAT,
                size=self.size
            )
            
            self.memory = mmap.mmap(self.shm.fd, self.size)
            logger.info(f"Zero-copy pipeline initialized: {self.name}, size={self.size}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            self.use_fallback = True
            return True
    
    def write_tick(self, tick: MarketDataTick, offset: int = 0) -> bool:
        """Write tick to shared memory at offset"""
        if self.use_fallback:
            self.fallback_buffer[offset] = tick
            return True
        
        if not self.memory:
            return False
        
        try:
            data = tick.to_bytes()
            if len(data) + offset > self.size:
                logger.warning("Data exceeds shared memory size")
                return False
            
            self.memory.seek(offset)
            self.memory.write(data)
            return True
        except Exception as e:
            logger.error(f"Write error: {e}")
            return False
    
    def read_tick(self, offset: int = 0) -> Optional[MarketDataTick]:
        """Read tick from shared memory at offset"""
        if self.use_fallback:
            return self.fallback_buffer.get(offset)
        
        if not self.memory:
            return None
        
        try:
            self.memory.seek(offset)
            data = b''
            while len(data) < 4096:
                byte = self.memory.read(1)
                if byte == b'\x00':
                    break
                data += byte
            
            if data:
                return MarketDataTick.from_bytes(data)
            return None
        except Exception as e:
            logger.error(f"Read error: {e}")
            return None
    
    def cleanup(self):
        """Cleanup shared memory"""
        if self.memory:
            self.memory.close()
        if self.shm:
            self.shm.unlink()
        logger.info("Zero-copy pipeline cleaned up")

def get_optimized_event_loop():
    """Get optimized event loop (try uvloop if available)"""
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("Using uvloop for optimized event loop")
    except ImportError:
        logger.info("uvloop not available, using default asyncio event loop")
    
    return asyncio.new_event_loop()

if __name__ == "__main__":
    async def test_feed():
        symbols = ["BTCUSDT", "ETHUSDT"]
        manager = AsyncWebSocketManager(symbols)
        
        def print_tick(tick):
            print(f"{tick.symbol}: ${tick.price:.2f} @ {tick.timestamp}")
        
        manager.add_callback(print_tick)
        
        try:
            await manager.start()
        except KeyboardInterrupt:
            await manager.stop()
    
    loop = get_optimized_event_loop()
    try:
        loop.run_until_complete(test_feed())
    except KeyboardInterrupt:
        print("Stopped")
