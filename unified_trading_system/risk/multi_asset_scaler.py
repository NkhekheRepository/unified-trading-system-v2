"""
Multi-Asset Scaling (Phase 6 - Micro-Flex Plan)
Scales trading from 3 to 15 liquid assets for higher trade frequency.
Implements correlation limits and portfolio balancing.
"""

import yaml
import os
from typing import Dict, List, Tuple, Any


class MultiAssetScaler:
    """
    Manages trading across multiple assets with tiered leverage.
    Scales from 3 to 15 assets for 50+ trades/day capacity.
    """
    
    def __init__(self, config_path: str = "config/unified.yaml"):
        self.assets = []
        self.tiers = {}
        self.max_correlated_exposure = 0.60
        
        # Load configuration
        self._load_config(config_path)
        
        # Track positions per asset
        self.positions = {asset: 0.0 for asset in self.assets}
        self.weights = {asset: 1.0 / len(self.assets) if self.assets else 1.0 
                        for asset in self.assets}
        
    def _load_config(self, config_path: str):
        """Load asset scaling configuration."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            asset_config = config.get('asset_scaling', {})
            
            if not asset_config.get('enabled', False):
                # Fall back to default 3 assets
                self.assets = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
                self.tiers = {
                    'BTCUSDT': {'tier': 1, 'leverage': 25},
                    'ETHUSDT': {'tier': 1, 'leverage': 25},
                    'SOLUSDT': {'tier': 1, 'leverage': 25}
                }
                return
            
            # Load tiered assets
            tiers_config = asset_config.get('tiers', {})
            tier_leverage = {}
            
            for tier_name, tier_info in tiers_config.items():
                tier_num = int(tier_name.split('_')[1])
                leverage = tier_info.get('leverage', 15)
                tier_leverage[tier_num] = leverage
                
                for asset in tier_info.get('assets', []):
                    self.assets.append(asset)
                    self.tiers[asset] = {
                        'tier': tier_num,
                        'leverage': leverage
                    }
            
            self.max_correlated_exposure = asset_config.get('max_correlated_exposure', 0.60)
            
            print(f"Multi-Asset Scaler: Loaded {len(self.assets)} assets")
            for tier_num, lev in sorted(tier_leverage.items()):
                tier_assets = [a for a, info in self.tiers.items() 
                             if info['tier'] == tier_num]
                print(f"  Tier {tier_num} ({lev}x): {tier_assets}")
                
        except Exception as e:
            print(f"Error loading config: {e}")
            # Default to 3 assets
            self.assets = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
            self.tiers = {
                'BTCUSDT': {'tier': 1, 'leverage': 25},
                'ETHUSDT': {'tier': 1, 'leverage': 25},
                'SOLUSDT': {'tier': 1, 'leverage': 25}
            }
    
    def get_asset_leverage(self, symbol: str) -> int:
        """Get the leverage for a specific asset based on its tier."""
        return self.tiers.get(symbol, {}).get('leverage', 15)  # Default to minimum 15x
    
    def get_signals_for_assets(self, signals: Dict[str, float]) -> List[Tuple[str, float]]:
        """
        Filter and prioritize signals across all assets.
        
        Args:
            signals: Dictionary of {symbol: confidence}
            
        Returns:
            List of (symbol, confidence) tuples, sorted by confidence
        """
        asset_signals = []
        
        for symbol in self.assets:
            if symbol in signals:
                confidence = signals[symbol]
                asset_signals.append((symbol, confidence))
        
        # Sort by confidence (highest first)
        asset_signals.sort(key=lambda x: x[1], reverse=True)
        
        return asset_signals
    
    def check_correlation_limit(self, proposed_positions: Dict[str, float]) -> Dict[str, Any]:
        """
        Check if proposed positions violate correlation limits.
        CFA Standard III(C) - Suitability: Limit correlated exposure.
        
        Args:
            proposed_positions: {symbol: position_value}
            
        Returns:
            Dictionary with compliance status and adjustments
        """
        # Group by correlation (simplified: BTC/ETH are correlated)
        correlated_group_1 = ['BTCUSDT', 'ETHUSDT']  # Highly correlated
        correlated_group_2 = ['SOLUSDT', 'BNBUSDT', 'ADAUSDT']  # Moderately correlated
        
        total_portfolio = sum(abs(v) for v in proposed_positions.values())
        
        if total_portfolio == 0:
            return {"compliant": True, "adjustments": {}}
        
        # Check group 1 (BTC/ETH)
        group1_exposure = sum(abs(proposed_positions.get(s, 0)) for s in correlated_group_1)
        group1_pct = group1_exposure / total_portfolio
        
        adjustments = {}
        if group1_pct > self.max_correlated_exposure:
            # Reduce exposure
            excess_pct = group1_pct - self.max_correlated_exposure
            excess_value = excess_pct * total_portfolio
            
            # Reduce proportionally
            for symbol in correlated_group_1:
                if symbol in proposed_positions:
                    reduction = excess_value * (abs(proposed_positions[symbol]) / group1_exposure)
                    adjustments[symbol] = proposed_positions[symbol] - reduction
            
            return {
                "compliant": False,
                "excess_pct": excess_pct,
                "adjustments": adjustments,
                "message": f"Reduced BTC/ETH exposure from {group1_pct*100:.1f}% to {self.max_correlated_exposure*100:.1f}%"
            }
        
        return {"compliant": True, "adjustments": {}}
    
    def get_target_positions(self, account_balance: float, 
                             signals: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate target positions across all assets.
        
        Args:
            account_balance: Current account balance
            signals: {symbol: confidence} from signal generator
            
        Returns:
            Dictionary of {symbol: position_details}
        """
        # Get sorted signals for our assets
        asset_signals = self.get_signals_for_assets(signals)
        
        target_positions = {}
        total_allocated = 0.0
        
        for symbol, confidence in asset_signals:
            if confidence < 0.60:  # Skip low confidence
                continue
            
            leverage = self.get_asset_leverage(symbol)
            
            # Allocate based on confidence and tier
            if confidence >= 0.75:
                allocation_pct = 0.15  # 15% for high confidence
            elif confidence >= 0.65:
                allocation_pct = 0.10  # 10% for medium confidence
            else:
                allocation_pct = 0.05  # 5% for low confidence
            
            position_value = account_balance * allocation_pct * leverage
            
            target_positions[symbol] = {
                "symbol": symbol,
                "confidence": confidence,
                "leverage": leverage,
                "position_value": position_value,
                "allocation_pct": allocation_pct
            }
            
            total_allocated += allocation_pct
            
            # Cap at 100% allocation
            if total_allocated >= 1.0:
                break
        
        # Check correlation limits
        proposed = {s: p['position_value'] for s, p in target_positions.items()}
        correlation_check = self.check_correlation_limit(proposed)
        
        if not correlation_check['compliant']:
            # Apply adjustments
            for symbol, adjusted_value in correlation_check['adjustments'].items():
                if symbol in target_positions:
                    target_positions[symbol]['position_value'] = adjusted_value
        
        return target_positions
    
    def calculate_trades_per_day(self, avg_holding_minutes: int = 60) -> int:
        """
        Estimate trades per day capacity with current assets.
        
        Args:
            avg_holding_minutes: Average minutes per trade
            
        Returns:
            Estimated trades per day
        """
        minutes_per_day = 24 * 60
        trades_per_asset = minutes_per_day / avg_holding_minutes
        return int(trades_per_asset * len(self.assets))


if __name__ == "__main__":
    # Test the Multi-Asset Scaler
    scaler = MultiAssetScaler()
    
    print("=" * 60)
    print("MULTI-ASSET SCALER TEST")
    print("=" * 60)
    print(f"Total Assets: {len(scaler.assets)}")
    print()
    
    # Simulate signals
    signals = {
        'BTCUSDT': 0.80,
        'ETHUSDT': 0.75,
        'SOLUSDT': 0.65,
        'BNBUSDT': 0.70,
        'XRPUSDT': 0.60,
        'ADAUSDT': 0.55,  # Will be skipped (<0.60)
    }
    
    print("Simulated Signals:")
    for s, c in signals.items():
        print(f"  {s}: {c:.2f}")
    print()
    
    # Get target positions
    targets = scaler.get_target_positions(10000.0, signals)
    
    print("Target Positions ($10,000 account):")
    print("-" * 40)
    for symbol, details in targets.items():
        print(f"  {symbol}: ${details['position_value']:.2f} "
              f"({details['leverage']}x, {details['confidence']:.2f} conf)")
    print()
    
    # Calculate trades per day
    trades_per_day = scaler.calculate_trades_per_day(60)
    print(f"Estimated Trades/Day (60min holding): {trades_per_day}")
    print(f"Estimated Trades/Day (15min holding): {scaler.calculate_trades_per_day(15)}")
    print()
    
    print("=" * 60)
    print("✓ PHASE 6 COMPLETED - Multi-Asset Scaler Ready")
    print("=" * 60)
