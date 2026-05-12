import json
import os

def cleanse_trade_journal(file_path):
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    with open(file_path, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("Error decoding JSON")
            return

    original_count = len(data)
    # We can't perfectly know which ones were "fake" since they were integrated
    # But based on the auditor's report, those trades had specifically high consistency
    # in confidence (0.7-0.95) and expected_return (0.008-0.02) 
    # while the logic for 'fake' returns was a simplified random range.
    
    cleansed_data = {}
    removed_count = 0

    for trade_id, trade in data.items():
        meta = trade.get('metadata', {})
        conf = meta.get('confidence', 0)
        pred_ret = trade.get('predicted_return', 0)
        
        # Filter out trades that perfectly match the 'demo' distribution
        # and exhibit suspect patterns (e.g., perfectly aligned’ synthetic returns)
        # In a real scenario, we'd look for the 'cycle' metadata associated with demo runs.
        if conf > 0.7 and 0.007 < pred_ret < 0.021:
            # Since we cannot be 100% sure without a 'demo' flag, 
            # we mark these as 'suspect' or remove if we want a clean slate.
            # For Institutional audit standards, any contaminated data is purged.
            removed_count += 1
            continue
        
        cleansed_data[trade_id] = trade

    with open(file_path + ".cleansed", 'w') as f:
        json.dump(cleansed_data, f, indent=2)

    print(f"Original Trades: {original_count}")
    print(f"Removed Suspect Trades: {removed_count}")
    print(f"Cleansed Trades: {len(cleansed_data)}")
    print(f"Saved to {file_path}.cleansed")

if __name__ == "__main__":
    cleanse_trade_journal('/home/nkhekhe/unified_trading_system/logs/trade_journal.json')
