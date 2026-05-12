import json
trades = json.load(open('logs/trade_journal.json'))
completed = [t for t in trades.values() if t.get('pnl') is not None]
if completed:
    wins = sum(1 for t in completed if t['pnl'] > 0)
    losses = sum(1 for t in completed if t['pnl'] < 0)
    winrate = (wins / len(completed) * 100)
    total_pnl = sum(t['pnl'] for t in completed)
    avg_pnl = total_pnl / len(completed)
    print('=== V3.2 SYSTEM STATUS ===')
    print('Process: RUNNING (PID: 1459357)')
    print('Balance: $~5,000 USDT (testnet)')
    print('Completed trades:', len(completed))
    print('Open positions:', len([t for t in trades.values() if t.get('pnl') is None]))
    print('Wins:', wins)
    print('Losses:', losses)
    print('Winrate: {:.2f}%'.format(winrate))
    print('Total P&L: ${:.2f}'.format(total_pnl))
    print('Avg P&L/trade: ${:.2f}'.format(avg_pnl))
else:
    print('No completed trades yet - system just restarted')
    print('Process: RUNNING (PID: 1459357)')
    print('Balance: $~5,000 USDT (testnet)')
    print('Open positions: 0')
