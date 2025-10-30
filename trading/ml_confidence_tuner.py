"""
Machine Learning Confidence Tuner for Enhanced Signal Scoring
Implements ML-based confidence enhancement using historical trade performance
"""

import logging
import pickle
import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import joblib

logger = logging.getLogger(__name__)

class MLConfidenceTuner:
    """
    Advanced ML-based confidence tuning system for signal enhancement
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.ml_config = config.get('trading', {}).get('ml_confidence_tuner', {})
        
        # Model configuration
        self.model_path = Path("models/confidence_model_v2.pkl")
        self.trade_history_path = Path("data/trade_history.json")
        self.feature_scaler_path = Path("models/feature_scaler.pkl")
        
        # Ensure directories exist
        self.model_path.parent.mkdir(exist_ok=True)
        self.trade_history_path.parent.mkdir(exist_ok=True)
        
        # Initialize components
        self.trade_history = self.load_trade_history()
        self.model = self.load_model()
        self.feature_scaler = self.load_feature_scaler()
        
        # Training parameters
        self.min_training_samples = self.ml_config.get('min_training_samples', 100)
        self.retrain_frequency_days = self.ml_config.get('retrain_frequency_days', 7)
        self.last_retrain_date = self.load_last_retrain_date()
        
        logger.info("🤖 ML Confidence Tuner initialized")
    
    def load_trade_history(self) -> List[Dict]:
        """Load historical trade data for training"""
        try:
            if self.trade_history_path.exists():
                with open(self.trade_history_path, 'r') as f:
                    history = json.load(f)
                logger.info(f"📊 Loaded {len(history)} historical trades")
                return history
            else:
                logger.info("📊 No trade history found, starting fresh")
                return []
        except Exception as e:
            logger.error(f"❌ Error loading trade history: {e}")
            return []
    
    def save_trade_history(self):
        """Save trade history to disk"""
        try:
            with open(self.trade_history_path, 'w') as f:
                json.dump(self.trade_history, f, indent=2, default=str)
            logger.debug(f"💾 Saved {len(self.trade_history)} trades to history")
        except Exception as e:
            logger.error(f"❌ Error saving trade history: {e}")
    
    def load_model(self) -> RandomForestClassifier:
        """Load or create ML model"""
        try:
            if self.model_path.exists():
                model = joblib.load(self.model_path)
                logger.info("🤖 Loaded existing ML confidence model")
                return model
            else:
                # Create new model with optimized parameters
                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1
                )
                logger.info("🤖 Created new ML confidence model")
                return model
        except Exception as e:
            logger.error(f"❌ Error loading model: {e}")
            return RandomForestClassifier(n_estimators=50, random_state=42)
    
    def save_model(self):
        """Save ML model to disk"""
        try:
            joblib.dump(self.model, self.model_path)
            logger.info("💾 ML confidence model saved")
        except Exception as e:
            logger.error(f"❌ Error saving model: {e}")
    
    def load_feature_scaler(self):
        """Load or create feature scaler"""
        try:
            if self.feature_scaler_path.exists():
                from sklearn.preprocessing import StandardScaler
                scaler = joblib.load(self.feature_scaler_path)
                logger.debug("📊 Loaded feature scaler")
                return scaler
            else:
                from sklearn.preprocessing import StandardScaler
                scaler = StandardScaler()
                logger.debug("📊 Created new feature scaler")
                return scaler
        except Exception as e:
            logger.error(f"❌ Error loading feature scaler: {e}")
            from sklearn.preprocessing import StandardScaler
            return StandardScaler()
    
    def save_feature_scaler(self):
        """Save feature scaler to disk"""
        try:
            joblib.dump(self.feature_scaler, self.feature_scaler_path)
            logger.debug("💾 Feature scaler saved")
        except Exception as e:
            logger.error(f"❌ Error saving feature scaler: {e}")
    
    def load_last_retrain_date(self) -> Optional[datetime]:
        """Load last retrain date"""
        try:
            retrain_file = Path("data/last_retrain.json")
            if retrain_file.exists():
                with open(retrain_file, 'r') as f:
                    data = json.load(f)
                return datetime.fromisoformat(data['last_retrain'])
            return None
        except Exception as e:
            logger.error(f"❌ Error loading last retrain date: {e}")
            return None
    
    def save_last_retrain_date(self, date: datetime):
        """Save last retrain date"""
        try:
            retrain_file = Path("data/last_retrain.json")
            retrain_file.parent.mkdir(exist_ok=True)
            with open(retrain_file, 'w') as f:
                json.dump({'last_retrain': date.isoformat()}, f)
        except Exception as e:
            logger.error(f"❌ Error saving last retrain date: {e}")
    
    def extract_features(self, signal_data: Dict) -> List[float]:
        """Extract features from signal data for ML model"""
        try:
            features = [
                signal_data.get('confidence', 0.5),
                signal_data.get('prediction_value', 0.5),
                signal_data.get('volatility', 0.1),
                signal_data.get('volume', 1000),
                signal_data.get('price_momentum', 0.0),
                signal_data.get('rsi', 50.0),
                signal_data.get('macd', 0.0),
                signal_data.get('bollinger_position', 0.5),
                signal_data.get('session_volatility_multiplier', 1.0),
                signal_data.get('time_of_day', 12.0),  # Hour of day
                signal_data.get('day_of_week', 3.0),   # Day of week
                signal_data.get('market_trend', 0.0),  # Overall market trend
            ]
            
            # Ensure all features are numeric
            features = [float(f) if f is not None else 0.0 for f in features]
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Error extracting features: {e}")
            return [0.5] * 12  # Default feature vector
    
    def add_trade_result(self, signal_data: Dict, trade_result: Dict):
        """Add completed trade to history for learning"""
        try:
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'features': self.extract_features(signal_data),
                'base_confidence': signal_data.get('confidence', 0.5),
                'enhanced_confidence': signal_data.get('enhanced_confidence', signal_data.get('confidence', 0.5)),
                'prediction_value': signal_data.get('prediction_value', 0.5),
                'epic': signal_data.get('epic', 'UNKNOWN'),
                'direction': signal_data.get('direction', 'BUY'),
                'entry_price': trade_result.get('entry_price', 0.0),
                'exit_price': trade_result.get('exit_price', 0.0),
                'pnl': trade_result.get('pnl', 0.0),
                'win': 1 if trade_result.get('pnl', 0.0) > 0 else 0,
                'duration_minutes': trade_result.get('duration_minutes', 0),
                'size': trade_result.get('size', 0.1)
            }
            
            self.trade_history.append(trade_record)
            
            # Keep only recent trades (last 1000)
            if len(self.trade_history) > 1000:
                self.trade_history = self.trade_history[-1000:]
            
            # Save updated history
            self.save_trade_history()
            
            logger.debug(f"📊 Added trade result to ML history: PnL={trade_result.get('pnl', 0.0):.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error adding trade result: {e}")
    
    def should_retrain(self) -> bool:
        """Check if model should be retrained"""
        try:
            # Check if we have enough data
            if len(self.trade_history) < self.min_training_samples:
                return False
            
            # Check if enough time has passed
            if self.last_retrain_date:
                days_since_retrain = (datetime.now() - self.last_retrain_date).days
                if days_since_retrain < self.retrain_frequency_days:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking retrain condition: {e}")
            return False
    
    def retrain_weekly(self) -> bool:
        """Retrain confidence model using recent trade history"""
        try:
            logger.info("🤖 Starting ML confidence model retraining...")
            
            if not self.should_retrain():
                logger.info("⏸️ Retraining not needed yet")
                return False
            
            # Get recent trades for training
            recent_trades = self.trade_history[-500:] if len(self.trade_history) > 500 else self.trade_history
            
            if len(recent_trades) < self.min_training_samples:
                logger.warning(f"⚠️ Insufficient data for retraining: {len(recent_trades)} < {self.min_training_samples}")
                return False
            
            # Prepare training data
            X = np.array([trade['features'] for trade in recent_trades])
            y = np.array([trade['win'] for trade in recent_trades])
            
            # Scale features
            X_scaled = self.feature_scaler.fit_transform(X)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Train model
            self.model.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            
            # Save model and scaler
            self.save_model()
            self.save_feature_scaler()
            
            # Update retrain date
            self.last_retrain_date = datetime.now()
            self.save_last_retrain_date(self.last_retrain_date)
            
            logger.info(f"✅ ML model retrained successfully:")
            logger.info(f"   Training samples: {len(recent_trades)}")
            logger.info(f"   Accuracy: {accuracy:.3f}")
            logger.info(f"   Precision: {precision:.3f}")
            logger.info(f"   Recall: {recall:.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error retraining model: {e}")
            return False
    
    def get_enhanced_confidence(self, signal_data: Dict) -> float:
        """Get ML-enhanced confidence score"""
        try:
            base_confidence = signal_data.get('confidence', 0.5)
            
            # Check if model is trained
            if not hasattr(self.model, 'feature_importances_'):
                logger.debug("🤖 Model not trained yet, using base confidence")
                return base_confidence
            
            # Extract and scale features
            features = self.extract_features(signal_data)
            features_array = np.array([features])
            
            # Scale features if scaler is fitted
            if hasattr(self.feature_scaler, 'mean_'):
                features_scaled = self.feature_scaler.transform(features_array)
            else:
                features_scaled = features_array
            
            # Get ML prediction probability
            try:
                ml_proba = self.model.predict_proba(features_scaled)[0]
                ml_boost = ml_proba[1] if len(ml_proba) > 1 else 0.5
            except Exception:
                ml_boost = 0.5
            
            # Combine base confidence with ML boost
            ml_weight = self.ml_config.get('ml_weight', 0.3)
            base_weight = 1.0 - ml_weight
            
            enhanced_confidence = (base_confidence * base_weight) + (ml_boost * ml_weight)
            
            # Cap at maximum confidence
            max_confidence = self.ml_config.get('max_confidence', 0.95)
            enhanced_confidence = min(enhanced_confidence, max_confidence)
            
            # Ensure minimum confidence
            min_confidence = self.ml_config.get('min_confidence', 0.1)
            enhanced_confidence = max(enhanced_confidence, min_confidence)
            
            logger.debug(f"🤖 ML Enhancement: {base_confidence:.3f} → {enhanced_confidence:.3f} (boost: {ml_boost:.3f})")
            
            return enhanced_confidence
            
        except Exception as e:
            logger.error(f"❌ Error enhancing confidence: {e}")
            return signal_data.get('confidence', 0.5)
    
    def get_model_stats(self) -> Dict:
        """Get model performance statistics"""
        try:
            stats = {
                'total_trades': len(self.trade_history),
                'model_trained': hasattr(self.model, 'feature_importances_'),
                'last_retrain': self.last_retrain_date.isoformat() if self.last_retrain_date else None,
                'days_since_retrain': (datetime.now() - self.last_retrain_date).days if self.last_retrain_date else None,
                'should_retrain': self.should_retrain(),
                'min_training_samples': self.min_training_samples,
                'retrain_frequency_days': self.retrain_frequency_days
            }
            
            if len(self.trade_history) > 0:
                recent_trades = self.trade_history[-100:] if len(self.trade_history) > 100 else self.trade_history
                win_rate = sum(t['win'] for t in recent_trades) / len(recent_trades)
                avg_pnl = sum(t['pnl'] for t in recent_trades) / len(recent_trades)
                
                stats.update({
                    'recent_win_rate': win_rate,
                    'recent_avg_pnl': avg_pnl,
                    'recent_trades_count': len(recent_trades)
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting model stats: {e}")
            return {'error': str(e)}
