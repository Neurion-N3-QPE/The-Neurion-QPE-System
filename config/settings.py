"""
Settings Manager - Configuration Loading
"""

import json
from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger(__name__)


DEFAULT_CONFIG = {
    'profile': 'balanced',
    'risk_per_trade': 0.02,
    'max_positions': 5,
    'confidence_threshold': 0.70,
    'update_interval': 60,
    'brokers': {
        'ig_markets': {
            'enabled': False,
            'api_key': '',
            'account_id': ''
        },
        'ic_markets': {
            'enabled': False,
            'api_key': '',
            'account_id': ''
        }
    }
}


def load_config(config_path: str = 'config/config.json') -> Dict:
    """
    Load configuration file
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        logger.warning(f"⚠️  Config file not found: {config_path}")
        logger.info("📝 Using default configuration")
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Merge with defaults
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)
        
        logger.info(f"✅ Configuration loaded from {config_path}")
        return merged_config
        
    except Exception as e:
        logger.error(f"❌ Error loading config: {e}")
        logger.info("📝 Using default configuration")
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict, config_path: str = 'config/config.json'):
    """
    Save configuration file
    
    Args:
        config: Configuration dictionary
        config_path: Path to save config
    """
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"✅ Configuration saved to {config_path}")
        
    except Exception as e:
        logger.error(f"❌ Error saving config: {e}")
