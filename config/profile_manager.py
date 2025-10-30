"""
Profile Manager - Risk Profile Configuration
Manages conservative, balanced, and aggressive trading profiles
"""

from typing import Dict
import logging

logger = logging.getLogger(__name__)


PROFILES = {
    'conservative': {
        'name': 'Conservative',
        'description': 'Low risk, high confidence trades only',
        'risk_per_trade': 0.01,  # 1% risk per trade
        'max_positions': 3,
        'confidence_threshold': 0.85,  # Very high confidence required
        'update_interval': 300,  # 5 minutes
        'position_sizing': {
            'min_multiplier': 0.5,
            'max_multiplier': 0.8
        },
        'stop_loss': 0.02,  # 2%
        'take_profit': 0.04  # 4% (2:1 RR)
    },
    
    'balanced': {
        'name': 'Balanced',
        'description': 'Balanced risk-reward approach',
        'risk_per_trade': 0.02,  # 2% risk per trade
        'max_positions': 5,
        'confidence_threshold': 0.70,  # Moderate confidence
        'update_interval': 60,  # 1 minute
        'position_sizing': {
            'min_multiplier': 0.3,
            'max_multiplier': 1.0
        },
        'stop_loss': 0.025,  # 2.5%
        'take_profit': 0.05  # 5% (2:1 RR)
    },
    
    'aggressive': {
        'name': 'Aggressive',
        'description': 'Higher risk, more trades, larger positions',
        'risk_per_trade': 0.03,  # 3% risk per trade
        'max_positions': 8,
        'confidence_threshold': 0.65,  # Lower confidence acceptable
        'update_interval': 30,  # 30 seconds
        'position_sizing': {
            'min_multiplier': 0.5,
            'max_multiplier': 1.5
        },
        'stop_loss': 0.03,  # 3%
        'take_profit': 0.06  # 6% (2:1 RR)
    }
}


class ProfileManager:
    """
    Manages trading profiles
    """
    
    def __init__(self):
        self.current_profile = 'balanced'
        self.profiles = PROFILES.copy()
        
    def get_profile(self, profile_name: str = None) -> Dict:
        """
        Get a trading profile
        
        Args:
            profile_name: Name of profile (conservative, balanced, aggressive)
                         If None, returns current profile
        
        Returns:
            Profile configuration dictionary
        """
        if profile_name is None:
            profile_name = self.current_profile
        
        if profile_name not in self.profiles:
            logger.warning(f"⚠️  Unknown profile: {profile_name}, using balanced")
            profile_name = 'balanced'
        
        return self.profiles[profile_name].copy()
    
    def set_profile(self, profile_name: str) -> Dict:
        """
        Set the current profile
        
        Args:
            profile_name: Name of profile to activate
            
        Returns:
            The activated profile configuration
        """
        if profile_name not in self.profiles:
            logger.error(f"❌ Unknown profile: {profile_name}")
            raise ValueError(f"Profile '{profile_name}' not found")
        
        self.current_profile = profile_name
        profile = self.profiles[profile_name]
        
        logger.info(f"✅ Profile set to: {profile['name']}")
        logger.info(f"   Risk/Trade: {profile['risk_per_trade']:.1%}")
        logger.info(f"   Max Positions: {profile['max_positions']}")
        logger.info(f"   Confidence: {profile['confidence_threshold']:.2f}")
        
        return profile.copy()
    
    def list_profiles(self) -> Dict[str, str]:
        """
        List all available profiles
        
        Returns:
            Dictionary of profile names and descriptions
        """
        return {
            name: profile['description']
            for name, profile in self.profiles.items()
        }
    
    def create_custom_profile(
        self,
        name: str,
        config: Dict
    ):
        """
        Create a custom profile
        
        Args:
            name: Custom profile name
            config: Profile configuration
        """
        # Validate config has required fields
        required = ['risk_per_trade', 'max_positions', 'confidence_threshold']
        for field in required:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        
        self.profiles[name] = config
        logger.info(f"✅ Custom profile created: {name}")
    
    def get_current_profile_name(self) -> str:
        """Get name of current profile"""
        return self.current_profile
