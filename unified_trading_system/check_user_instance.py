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
    print('=== NEW INSTANCE PERFORMANCE ===')
    print('Process: RUNNING (PID: 1469768)')
    print('API Key: iDlc0QMUTLUk5iUeqjy6suNg5oIfSa6d23JOHBHUQHdMn7cc4yyukZQ9IrJaDFqq')
    print('Completed trades:', len(completed))
    print('Wins:', wins)
    print('Losses:', losses)
    print('Winrate: {:.2f}%'.format(winrate))
    print('Total P&L: ${:.2f}'.format(total_pnl))
    print('Avg P&L/trade: ${:.2f}'.format(avg_pnl))
else:
    print('')
    print('No completed trades yet - new instance just started')
    print('Process: RUNNING (PID: 1469768)')
    print('API Key: iDlc0QMUTLUk5iUeqjy6suNg5oIfSa6d23JOHBHUQHdMn7cc4yyukZQ9IrJaDFqq')
