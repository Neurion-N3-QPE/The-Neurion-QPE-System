"""
Settings Manager - Configuration Loading
"""

import json
from pathlib import Path
from typing import Dict
import logging
import os
from dotenv import load_dotenv, set_key

load_dotenv() # Load environment variables from .env file

logger = logging.getLogger(__name__)


DEFAULT_CONFIG = {
    'profile': 'balanced',
    'risk_per_trade': 0.02,
    'max_positions': 5,
    'confidence_threshold': 0.70,
    'update_interval': 60,
    'brokers': {
        'ig_markets': {
            'enabled': os.getenv('IG_MARKETS_MODE', 'live') == 'live',
            'api_key': os.getenv('IG_MARKETS_API_KEY', ''),
            'username': os.getenv('IG_MARKETS_USERNAME', ''),
            'password': os.getenv('IG_MARKETS_PASSWORD', ''),
            'account_id': os.getenv('IG_MARKETS_ACCOUNT_ID', ''),
            'demo': os.getenv('IG_MARKETS_MODE', 'live') == 'demo',
            'default_epic': os.getenv('DEFAULT_SYMBOLS', 'IX.D.SPTRD.DAILY.IP').split(',')[0]  # Default to S&P 500 DFB
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

        # Ensure 'brokers' and 'ig_markets' keys exist
        if 'brokers' not in merged_config:
            merged_config['brokers'] = {}
        if 'ig_markets' not in merged_config['brokers']:
            merged_config['brokers']['ig_markets'] = {}

        # Override with environment variables if present
        ig_markets_config = merged_config['brokers']['ig_markets']
        ig_markets_config['api_key'] = os.getenv('IG_MARKETS_API_KEY', ig_markets_config.get('api_key', ''))
        ig_markets_config['username'] = os.getenv('IG_MARKETS_USERNAME', ig_markets_config.get('username', ''))
        ig_markets_config['password'] = os.getenv('IG_MARKETS_PASSWORD', ig_markets_config.get('password', ''))
        ig_markets_config['account_id'] = os.getenv('IG_MARKETS_ACCOUNT_ID', ig_markets_config.get('account_id', ''))
        ig_markets_config['demo'] = os.getenv('IG_MARKETS_MODE', 'live') == 'demo'
        ig_markets_config['default_epic'] = os.getenv('DEFAULT_SYMBOLS', 'IX.D.SPTRD.DAILY.IP').split(',')[0]  # Default to S&P 500 DFB
        ig_markets_config['enabled'] = os.getenv('IG_MARKETS_MODE', 'live') == 'live' # Ensure enabled status is correct

        merged_config['risk_per_trade'] = float(os.getenv('RISK_PER_TRADE', merged_config.get('risk_per_trade', DEFAULT_CONFIG['risk_per_trade'])))
        merged_config['max_positions'] = int(os.getenv('MAX_POSITIONS', merged_config.get('max_positions', DEFAULT_CONFIG['max_positions'])))
        merged_config['confidence_threshold'] = float(os.getenv('CONFIDENCE_THRESHOLD', merged_config.get('confidence_threshold', DEFAULT_CONFIG['confidence_threshold'])))
        merged_config['update_interval'] = int(os.getenv('UPDATE_INTERVAL', merged_config.get('update_interval', DEFAULT_CONFIG['update_interval'])))
        
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


def update_env_var(key: str, value: str, env_file: str = '.env'):
    """
    Update environment variable in .env file

    Args:
        key: Environment variable name
        value: Environment variable value
        env_file: Path to .env file
    """
    try:
        env_path = Path(env_file)
        if not env_path.exists():
            logger.warning(f"⚠️  .env file not found: {env_file}")
            return False

        # Update the .env file
        set_key(str(env_path), key, value)

        # Also update the current environment
        os.environ[key] = value

        logger.debug(f"✅ Updated {key} = {value}")
        return True

    except Exception as e:
        logger.error(f"❌ Error updating environment variable {key}: {e}")
        return False
