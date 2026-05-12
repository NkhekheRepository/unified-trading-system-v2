#!/usr/bin/env python3
"""
JSON Recovery Script - Extracts valid trades from corrupted trade_journal.json
"""

import json
import os
import sys
from datetime import datetime

INPUT_FILE = '/home/nkhekhe/unified_trading_system/logs/trade_journal.json'
OUTPUT_FILE = '/home/nkhekhe/unified_trading_system/logs/trade_journal_fixed.json'
FAILED_FILE = '/home/nkhekhe/unified_trading_system/logs/failed_trades.json'

def main():
    print("="*60)
    print("JSON RECOVERY - TRADE JOURNAL")
    print("="*60)
    
    # Try full file parse first
    print("\n[1] Trying full file parse...")
    try:
        with open(INPUT_FILE, 'r') as f:
            data = json.load(f)
        print(f"✅ SUCCESS: File is valid JSON with {len(data)} entries")
        print("No recovery needed!")
        return
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: {e}")
        print(f"   Position: {e.pos}, Line: {e.lineno}, Col: {e.colno}")
    
    # Line-by-line recovery
    print("\n[2] Attempting line-by-line recovery...")
    
    valid_trades = {}
    failed_trades = []
    line_num = 0
    
    with open(INPUT_FILE, 'r') as f:
        for line in f:
            line_num += 1
            line = line.strip()
            
            if not line or line == '{' or line == '}' or line == '[' or line == '],':
                continue
            
            # Try to parse each line as a JSON object
            try:
                # Handle potential trailing commas
                if line.endswith(','):
                    line = line[:-1]
                
                # Try parsing
                trade = json.loads(line)
                
                # Validate it's a trade (has required fields)
                if 'trade_id' in trade and 'symbol' in trade:
                    valid_trades[trade['trade_id']] = trade
                else:
                    # Might be a container object
                    if isinstance(trade, dict):
                        for key, value in trade.items():
                            if isinstance(value, dict) and 'trade_id' in value:
                                valid_trades[value['trade_id']] = value
                                
            except (json.JSONDecodeError, Exception) as e:
                failed_trades.append({'line': line_num, 'error': str(e)[:100]})
    
    print(f"\n[3] Recovery Results:")
    print(f"   Valid trades: {len(valid_trades)}")
    print(f"   Failed lines: {len(failed_trades)}")
    
    # Save valid trades
    print(f"\n[4] Saving valid trades to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(valid_trades, f, indent=2)
    
    # Save failed entries
    print(f"Saving failed entries to {FAILED_FILE}...")
    with open(FAILED_FILE, 'w') as f:
        json.dump({
            'failed_count': len(failed_trades),
            'entries': failed_trades[:100]  # First 100 only
        }, f, indent=2)
    
    # Verify the fixed file
    print(f"\n[5] Verifying fixed file...")
    try:
        with open(OUTPUT_FILE, 'r') as f:
            test_data = json.load(f)
        print(f"✅ VERIFIED: Fixed file has {len(test_data)} valid entries")
        
        # Show sample entry
        sample_id = list(test_data.keys())[0]
        sample = test_data[sample_id]
        print(f"\n   Sample trade: {sample_id}")
        print(f"   - Symbol: {sample.get('symbol')}")
        print(f"   - Side: {sample.get('side')}")
        print(f"   - Status: {sample.get('status')}")
        
    except json.JSONDecodeError as e:
        print(f"❌ VERIFICATION FAILED: {e}")
    
    print("\n" + "="*60)
    print("RECOVERY COMPLETE")
    print("="*60)
    print(f"Original: {INPUT_FILE}")
    print(f"Backup: {INPUT_FILE}.backup")
    print(f"Fixed: {OUTPUT_FILE}")
    print(f"Failed log: {FAILED_FILE}")

if __name__ == "__main__":
    main()