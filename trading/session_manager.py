"""
Session Manager for Time-Based Market Exposure
Implements session-bound exposure to optimize trading during peak market hours
"""

import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
import pytz

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Advanced session management for time-based market exposure optimization
    """
    
    # Trading session definitions with timezone-aware scheduling
    SESSIONS = {
        "asia": {
            "name": "Asian Session",
            "start": "00:00",
            "end": "08:00",
            "timezone": "Asia/Tokyo",
            "epics": ["IX.D.NIKKEI.DAILY.IP", "IX.D.HANGSENG.DAILY.IP"],
            "primary_epic": "IX.D.NIKKEI.DAILY.IP",
            "volatility_multiplier": 0.8,  # Lower volatility session
            "max_positions": 2
        },
        "europe": {
            "name": "European Session", 
            "start": "08:00",
            "end": "16:00",
            "timezone": "Europe/London",
            "epics": ["IX.D.FTSE.DAILY.IP", "IX.D.DAX.DAILY.IP", "IX.D.EUROSTOXX.DAILY.IP"],
            "primary_epic": "IX.D.FTSE.DAILY.IP",
            "volatility_multiplier": 1.0,  # Standard volatility
            "max_positions": 3
        },
        "us": {
            "name": "US Session",
            "start": "16:00", 
            "end": "23:00",
            "timezone": "America/New_York",
            "epics": ["IX.D.SPTRD.DAILY.IP", "IX.D.NASDAQ.DAILY.IP", "IX.D.DOW.DAILY.IP"],
            "primary_epic": "IX.D.SPTRD.DAILY.IP",
            "volatility_multiplier": 1.2,  # Higher volatility session
            "max_positions": 3
        },
        "overlap_eu_us": {
            "name": "EU-US Overlap",
            "start": "16:00",
            "end": "17:00", 
            "timezone": "Europe/London",
            "epics": ["IX.D.SPTRD.DAILY.IP", "IX.D.FTSE.DAILY.IP"],
            "primary_epic": "IX.D.SPTRD.DAILY.IP",
            "volatility_multiplier": 1.5,  # Highest volatility overlap
            "max_positions": 4
        }
    }
    
    def __init__(self, config: Dict):
        self.config = config
        self.session_config = config.get('trading', {}).get('session_bound_exposure', {})
        self.current_session = None
        self.session_start_time = None
        self.active_epics = []
        
        logger.info("📅 Session Manager initialized")
    
    def get_active_session_epics(self) -> List[str]:
        """
        Get epics for the currently active trading session
        Goal: Focus trading on most liquid markets during their peak hours
        """
        try:
            current_session = self.get_current_session()
            
            if current_session:
                epics = current_session.get('epics', [])
                logger.debug(f"📅 Active Session: {current_session['name']} | Epics: {len(epics)}")
                return epics
            else:
                # Fallback to default epics during off-hours
                default_epics = ["IX.D.SPTRD.DAILY.IP"]
                logger.debug(f"📅 Off-hours trading | Default epics: {default_epics}")
                return default_epics
                
        except Exception as e:
            logger.error(f"❌ Error getting active session epics: {e}")
            return ["IX.D.SPTRD.DAILY.IP"]  # Safe fallback
    
    def get_current_session(self) -> Optional[Dict]:
        """Get the currently active trading session"""
        try:
            current_utc = datetime.now(pytz.UTC)
            
            # Check for session overlaps first (highest priority)
            overlap_session = self._check_session_overlap(current_utc)
            if overlap_session:
                return overlap_session
            
            # Check regular sessions
            for session_name, session_config in self.SESSIONS.items():
                if session_name.startswith('overlap_'):
                    continue  # Skip overlap sessions in regular check
                    
                if self._is_session_active(session_config, current_utc):
                    return session_config
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting current session: {e}")
            return None
    
    def _check_session_overlap(self, current_utc: datetime) -> Optional[Dict]:
        """Check for high-priority session overlaps"""
        try:
            # Check EU-US overlap (16:00-17:00 London time)
            london_tz = pytz.timezone('Europe/London')
            london_time = current_utc.astimezone(london_tz)
            london_hour = london_time.hour
            
            if 16 <= london_hour < 17:  # EU-US overlap period
                overlap_config = self.SESSIONS.get('overlap_eu_us')
                if overlap_config:
                    logger.info(f"🔥 HIGH VOLATILITY OVERLAP: EU-US Session Active")
                    return overlap_config
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error checking session overlap: {e}")
            return None
    
    def _is_session_active(self, session_config: Dict, current_utc: datetime) -> bool:
        """Check if a specific session is currently active"""
        try:
            session_tz = pytz.timezone(session_config['timezone'])
            session_time = current_utc.astimezone(session_tz)
            current_hour = session_time.hour
            
            start_hour = int(session_config['start'].split(':')[0])
            end_hour = int(session_config['end'].split(':')[0])
            
            # Handle sessions that cross midnight
            if start_hour > end_hour:
                return current_hour >= start_hour or current_hour < end_hour
            else:
                return start_hour <= current_hour < end_hour
                
        except Exception as e:
            logger.error(f"❌ Error checking session activity: {e}")
            return False
    
    def get_session_volatility_multiplier(self) -> float:
        """Get volatility multiplier for the current session"""
        try:
            current_session = self.get_current_session()
            
            if current_session:
                multiplier = current_session.get('volatility_multiplier', 1.0)
                logger.debug(f"📊 Session volatility multiplier: {multiplier:.1f}x")
                return multiplier
            
            return 1.0  # Neutral multiplier
            
        except Exception as e:
            logger.error(f"❌ Error getting session volatility multiplier: {e}")
            return 1.0
    
    def get_session_max_positions(self) -> int:
        """Get maximum positions allowed for the current session"""
        try:
            current_session = self.get_current_session()
            
            if current_session:
                max_positions = current_session.get('max_positions', 3)
                logger.debug(f"📊 Session max positions: {max_positions}")
                return max_positions
            
            return 2  # Conservative fallback
            
        except Exception as e:
            logger.error(f"❌ Error getting session max positions: {e}")
            return 2
    
    def get_primary_epic_for_session(self) -> str:
        """Get the primary epic for the current session"""
        try:
            current_session = self.get_current_session()
            
            if current_session:
                primary_epic = current_session.get('primary_epic', 'IX.D.SPTRD.DAILY.IP')
                logger.debug(f"🎯 Primary epic for session: {primary_epic}")
                return primary_epic
            
            return 'IX.D.SPTRD.DAILY.IP'  # Default fallback
            
        except Exception as e:
            logger.error(f"❌ Error getting primary epic: {e}")
            return 'IX.D.SPTRD.DAILY.IP'
    
    def should_trade_epic(self, epic: str) -> bool:
        """Check if an epic should be traded in the current session"""
        try:
            active_epics = self.get_active_session_epics()
            should_trade = epic in active_epics
            
            if not should_trade:
                logger.debug(f"⏰ Epic {epic} not active in current session")
            
            return should_trade
            
        except Exception as e:
            logger.error(f"❌ Error checking if should trade epic {epic}: {e}")
            return True  # Conservative fallback - allow trading
    
    def get_session_info(self) -> Dict:
        """Get comprehensive information about the current session"""
        try:
            current_session = self.get_current_session()
            
            if current_session:
                return {
                    'session_name': current_session.get('name', 'Unknown'),
                    'active_epics': current_session.get('epics', []),
                    'primary_epic': current_session.get('primary_epic', 'IX.D.SPTRD.DAILY.IP'),
                    'volatility_multiplier': current_session.get('volatility_multiplier', 1.0),
                    'max_positions': current_session.get('max_positions', 3),
                    'timezone': current_session.get('timezone', 'UTC'),
                    'start_time': current_session.get('start', '00:00'),
                    'end_time': current_session.get('end', '23:59')
                }
            else:
                return {
                    'session_name': 'Off-Hours',
                    'active_epics': ['IX.D.SPTRD.DAILY.IP'],
                    'primary_epic': 'IX.D.SPTRD.DAILY.IP',
                    'volatility_multiplier': 0.8,
                    'max_positions': 2,
                    'timezone': 'UTC',
                    'start_time': '00:00',
                    'end_time': '23:59'
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting session info: {e}")
            return {
                'session_name': 'Error',
                'active_epics': ['IX.D.SPTRD.DAILY.IP'],
                'primary_epic': 'IX.D.SPTRD.DAILY.IP',
                'volatility_multiplier': 1.0,
                'max_positions': 2,
                'timezone': 'UTC',
                'start_time': '00:00',
                'end_time': '23:59'
            }
    
    def log_session_status(self):
        """Log current session status for monitoring"""
        try:
            session_info = self.get_session_info()
            
            logger.info(f"📅 SESSION STATUS:")
            logger.info(f"   Current Session: {session_info['session_name']}")
            logger.info(f"   Active Epics: {len(session_info['active_epics'])} ({', '.join(session_info['active_epics'])})")
            logger.info(f"   Primary Epic: {session_info['primary_epic']}")
            logger.info(f"   Volatility Multiplier: {session_info['volatility_multiplier']:.1f}x")
            logger.info(f"   Max Positions: {session_info['max_positions']}")
            logger.info(f"   Session Time: {session_info['start_time']} - {session_info['end_time']} ({session_info['timezone']})")
            
        except Exception as e:
            logger.error(f"❌ Error logging session status: {e}")
