import json
trades = json.load(open('logs/trade_journal.json'))
completed = [t for t in trades.values() if t.get('pnl') is not None]
if completed:
    wins = sum(1 for t in completed if t['pnl'] > 0)
    losses = sum(1 for t in completed if t['pnl'] < 0)
    winrate = (wins / len(completed) * 100)
    total_pnl = sum(t['pnl'] for t in completed)
    avg_pnl = total_pnl / len(completed)
    print('')
    print('=== ALL INSTANCES COMBINED PERFORMANCE ===')
    print('Completed trades: {}'.format(len(completed)))
    print('Wins: {}'.format(wins))
    print('Losses: {}'.format(losses))
    print('Winrate: {:.2f}%'.format(winrate))
    print('Total P&L: ${:.2f}'.format(total_pnl))
    print('Avg P&L/trade: ${:.2f}'.format(avg_pnl))
    print('')
    print('Recent trades:')
    recent_sorted = sorted(completed, key=lambda x: x.get('exit_time', 0), reverse=True)[:5]
    for i, t in enumerate(recent_sorted, 1):
        print('  {}. {} {} P&L: ${:.4f}'.format(i, t['symbol'], t['side'], t['pnl']))
else:
    print('')
    print('No completed trades yet')
