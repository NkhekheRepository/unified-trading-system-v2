#!/usr/bin/env python3
"""
Performance metrics calculator for the enhanced trading system.
It reads the trade journal, fetches current prices from Binance Testnet,
computes realized PnL, unrealized PnL, win rate, average profit, and writes a short report.
"""
import json, asyncio, aiohttp, os

JOURNAL = os.path.expanduser('~/unified_trading_system/logs/trade_journal.json')
BASE_URL = 'https://testnet.binancefuture.com'

async def fetch_price(symbol):
    async with aiohttp.ClientSession() as s:
        url = f"{BASE_URL}/fapi/v1/ticker/24hr?symbol={symbol.replace('/','')}"
        async with s.get(url) as r:
            if r.status == 200:
                data = await r.json()
                return float(data.get('lastPrice') or ((float(data.get('bidPrice',0))+float(data.get('askPrice',0)))/2))
    return None

async def main():
    with open(JOURNAL) as f:
        data = json.load(f)
    # Separate closed and open trades
    closed = [t for t in data.values() if t.get('status') == 'CLOSED']
    open_trades = [t for t in data.values() if t.get('status') == 'OPEN']
    # Realized PnL
    realized = sum(t.get('pnl',0) or 0 for t in closed)
    wins = sum(1 for t in closed if (t.get('pnl',0) or 0) > 0)
    losses = sum(1 for t in closed if (t.get('pnl',0) or 0) < 0)
    # Fetch prices for open trades
    symbols = {t['symbol'] for t in open_trades}
    prices = {}
    for sym in symbols:
        prices[sym] = await fetch_price(sym)
    unrealized = 0.0
    for t in open_trades:
        cur = prices.get(t['symbol'])
        if cur is None:
            continue
        qty = t['quantity']
        entry = t['entry_price']
        side = t['side']
        pnl = (cur - entry) * qty if side == 'BUY' else (entry - cur) * qty
        unrealized += pnl
    total = realized + unrealized
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    avg_profit = (realized / len(closed)) if closed else 0
    report = [
        f"Realized PnL: {realized:.2f}",
        f"Unrealized PnL: {unrealized:.2f}",
        f"Total PnL: {total:.2f}",
        f"Closed trades: {len(closed)} (Wins: {wins}, Losses: {losses})",
        f"Win rate: {win_rate:.2f}%",
        f"Average realized profit per trade: {avg_profit:.4f}",
    ]
    out_path = os.path.expanduser('~/unified_trading_system/performance_report.txt')
    with open(out_path, 'w') as f:
        f.write('\n'.join(report))
    print('Report written to', out_path)

if __name__ == '__main__':
    asyncio.run(main())
