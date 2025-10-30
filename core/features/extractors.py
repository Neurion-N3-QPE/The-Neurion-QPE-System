"""
Migrated from: qpe_core\feature_extraction\extractors.py
Migration Date: 2025-10-30 08:11:55.299255
N3 QPE v2.0 - Neurion Quantum Predictive Engine
Target Performance: 99.8% Win Rate | Sharpe 26.74
"""

"""
N³ QPE Feature Extraction System
================================

Transforms raw signals into stress, liquidity, sentiment, and volatility vectors
using advanced signal processing and machine learning techniques.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import signal, stats
from scipy.fft import fft, fftfreq
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from ..config.settings import settings
from ..data_ingestion.ingestion import DataPoint, FeedType
from ..telemetry.logger import get_logger

logger = get_logger(__name__)


class VectorType(str, Enum):
    """Types of feature vectors"""

    STRESS = "stress"
    LIQUIDITY = "liquidity"
    SENTIMENT = "sentiment"
    VOLATILITY = "volatility"
    MOMENTUM = "momentum"
    CORRELATION = "correlation"


@dataclass
class FeatureVector:
    """Standardized feature vector output"""

    vector_type: VectorType
    timestamp: datetime
    values: np.ndarray
    confidence: float
    metadata: Dict[str, float] = field(default_factory=dict)
    source_signals: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate vector data"""
        if not isinstance(self.values, np.ndarray):
            self.values = np.array(self.values)

        # Ensure values are finite
        self.values = np.nan_to_num(self.values, nan=0.0, posinf=1.0, neginf=-1.0)

        # Normalize confidence to [0, 1]
        self.confidence = max(0.0, min(1.0, self.confidence))


class BaseFeatureExtractor:
    """Base class for feature extractors"""

    def __init__(self, window_size: int = 100, overlap: float = 0.5):
        self.window_size = window_size
        self.overlap = overlap
        self.scaler = StandardScaler()
        self.history: List[DataPoint] = []
        self.is_fitted = False

    def add_data(self, data_points: List[DataPoint]) -> None:
        """Add new data points to the processing history"""
        self.history.extend(data_points)

        # Keep only recent data within retention window
        cutoff_time = datetime.utcnow() - timedelta(hours=24)  # 24-hour rolling window
        self.history = [dp for dp in self.history if dp.timestamp > cutoff_time]

        # Sort by timestamp
        self.history.sort(key=lambda x: x.timestamp)

    def extract_features(self) -> Optional[FeatureVector]:
        """Extract features from current data window"""
        if len(self.history) < self.window_size:
            return None

        # Get the most recent window of data
        window_data = self.history[-self.window_size :]
        return self._process_window(window_data)

    def _process_window(self, data: List[DataPoint]) -> Optional[FeatureVector]:
        """Process a window of data - to be implemented by subclasses"""
        raise NotImplementedError


class StressVectorExtractor(BaseFeatureExtractor):
    """
    Extracts market stress indicators from financial data.
    Measures systemic risk, correlation breakdowns, and tail events.
    """

    def _process_window(self, data: List[DataPoint]) -> Optional[FeatureVector]:
        """Extract stress indicators"""
        try:
            # Convert to time series DataFrame
            df = self._to_dataframe(data)
            if df.empty or len(df.columns) < 2:
                return None

            # Calculate stress components
            volatility_stress = self._calculate_volatility_stress(df)
            correlation_stress = self._calculate_correlation_stress(df)
            tail_risk = self._calculate_tail_risk(df)
            liquidity_stress = self._calculate_liquidity_stress(df)

            # Combine into stress vector
            stress_vector = np.array(
                [
                    volatility_stress,
                    correlation_stress,
                    tail_risk,
                    liquidity_stress,
                    np.mean([volatility_stress, correlation_stress, tail_risk]),  # Composite stress
                ]
            )

            # Calculate confidence based on data quality
            confidence = self._calculate_confidence(df)

            return FeatureVector(
                vector_type=VectorType.STRESS,
                timestamp=datetime.utcnow(),
                values=stress_vector,
                confidence=confidence,
                metadata={
                    "volatility_stress": volatility_stress,
                    "correlation_stress": correlation_stress,
                    "tail_risk": tail_risk,
                    "liquidity_stress": liquidity_stress,
                },
                source_signals=list(df.columns),
            )

        except Exception as e:
            logger.error(f"Error extracting stress vector: {e}")
            return None

    def _to_dataframe(self, data: List[DataPoint]) -> pd.DataFrame:
        """Convert DataPoints to pivot DataFrame"""
        records = []
        for dp in data:
            records.append(
                {
                    "timestamp": dp.timestamp,
                    "signal": dp.signal_name,
                    "value": dp.value,
                    "confidence": dp.confidence,
                }
            )

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)

        # Pivot to get signals as columns
        pivot_df = (
            df.pivot_table(index="timestamp", columns="signal", values="value", aggfunc="mean")
            .fillna(method="ffill")
            .fillna(0)
        )

        return pivot_df

    def _calculate_volatility_stress(self, df: pd.DataFrame) -> float:
        """Calculate volatility-based stress indicator"""
        if df.empty:
            return 0.0

        # Calculate rolling volatility for each signal
        volatilities = []
        for col in df.columns:
            returns = df[col].pct_change().dropna()
            if len(returns) > 10:
                vol = returns.rolling(window=10).std().iloc[-1]
                volatilities.append(vol if not np.isnan(vol) else 0.0)

        if not volatilities:
            return 0.0

        # Stress is the 95th percentile of volatilities
        return np.percentile(volatilities, 95)

    def _calculate_correlation_stress(self, df: pd.DataFrame) -> float:
        """Calculate correlation breakdown stress"""
        if df.empty or len(df.columns) < 2:
            return 0.0

        try:
            # Calculate correlation matrix
            corr_matrix = df.corr()

            # Measure correlation instability
            # Higher stress when correlations are extreme (near ±1) or unstable
            correlation_values = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)]
            correlation_values = correlation_values[~np.isnan(correlation_values)]

            if len(correlation_values) == 0:
                return 0.0

            # Stress increases with extreme correlations
            extreme_corr_stress = np.mean(np.abs(correlation_values) > 0.8)

            return extreme_corr_stress

        except Exception:
            return 0.0

    def _calculate_tail_risk(self, df: pd.DataFrame) -> float:
        """Calculate tail risk indicator"""
        if df.empty:
            return 0.0

        tail_risks = []
        for col in df.columns:
            returns = df[col].pct_change().dropna()
            if len(returns) > 20:
                # Calculate Value at Risk (5th percentile)
                var_5 = np.percentile(returns, 5)
                # Normalize by standard deviation
                std_dev = returns.std()
                if std_dev > 0:
                    normalized_var = abs(var_5) / std_dev
                    tail_risks.append(normalized_var)

        return np.mean(tail_risks) if tail_risks else 0.0

    def _calculate_liquidity_stress(self, df: pd.DataFrame) -> float:
        """Calculate liquidity stress from bid-ask spreads and volume patterns"""
        if df.empty:
            return 0.0

        # Placeholder for liquidity stress calculation
        # In a real implementation, this would use bid-ask spread data
        # For now, use price impact as a proxy
        liquidity_indicators = []

        for col in df.columns:
            price_changes = df[col].diff().abs().rolling(window=5).mean()
            if not price_changes.empty:
                # Higher price impact indicates lower liquidity
                impact = price_changes.iloc[-1] if not np.isnan(price_changes.iloc[-1]) else 0.0
                liquidity_indicators.append(impact)

        return np.mean(liquidity_indicators) if liquidity_indicators else 0.0

    def _calculate_confidence(self, df: pd.DataFrame) -> float:
        """Calculate confidence based on data completeness and quality"""
        if df.empty:
            return 0.0

        # Data completeness
        completeness = 1.0 - (df.isnull().sum().sum() / (df.shape[0] * df.shape[1]))

        # Temporal consistency (no large gaps)
        if len(df) > 1:
            time_gaps = pd.Series(df.index).diff().dt.total_seconds()
            max_gap = time_gaps.max() if not time_gaps.empty else 0
            temporal_quality = 1.0 / (1.0 + max_gap / 3600)  # Penalty for gaps > 1 hour
        else:
            temporal_quality = 0.5

        # Signal diversity
        signal_diversity = min(1.0, len(df.columns) / 5)  # Optimal at 5+ signals

        return (completeness + temporal_quality + signal_diversity) / 3


class LiquidityVectorExtractor(BaseFeatureExtractor):
    """Extract liquidity indicators from market data"""

    def _process_window(self, data: List[DataPoint]) -> Optional[FeatureVector]:
        """Extract liquidity features"""
        try:
            df = self._to_dataframe(data)
            if df.empty:
                return None

            # Liquidity indicators
            bid_ask_spread = self._calculate_bid_ask_spread(df)
            market_depth = self._calculate_market_depth(df)
            price_impact = self._calculate_price_impact(df)
            turnover_ratio = self._calculate_turnover_ratio(df)

            liquidity_vector = np.array(
                [
                    1.0 - bid_ask_spread,  # Higher spread = lower liquidity
                    market_depth,
                    1.0 - price_impact,  # Higher impact = lower liquidity
                    turnover_ratio,
                    np.mean(
                        [1.0 - bid_ask_spread, market_depth, 1.0 - price_impact, turnover_ratio]
                    ),
                ]
            )

            confidence = min(0.9, len(df) / self.window_size)

            return FeatureVector(
                vector_type=VectorType.LIQUIDITY,
                timestamp=datetime.utcnow(),
                values=liquidity_vector,
                confidence=confidence,
                metadata={
                    "bid_ask_spread": bid_ask_spread,
                    "market_depth": market_depth,
                    "price_impact": price_impact,
                    "turnover_ratio": turnover_ratio,
                },
            )

        except Exception as e:
            logger.error(f"Error extracting liquidity vector: {e}")
            return None

    def _to_dataframe(self, data: List[DataPoint]) -> pd.DataFrame:
        """Convert to DataFrame (same as StressVectorExtractor)"""
        records = []
        for dp in data:
            records.append({"timestamp": dp.timestamp, "signal": dp.signal_name, "value": dp.value})

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        return (
            df.pivot_table(index="timestamp", columns="signal", values="value", aggfunc="mean")
            .fillna(method="ffill")
            .fillna(0)
        )

    def _calculate_bid_ask_spread(self, df: pd.DataFrame) -> float:
        """Calculate normalized bid-ask spread"""
        # Placeholder - would need actual bid/ask data
        return 0.1

    def _calculate_market_depth(self, df: pd.DataFrame) -> float:
        """Calculate market depth indicator"""
        # Placeholder - would need order book data
        return 0.8

    def _calculate_price_impact(self, df: pd.DataFrame) -> float:
        """Calculate price impact from volume and price changes"""
        # Placeholder implementation
        if df.empty:
            return 0.0

        price_volatility = df.std(axis=1).mean()
        return min(1.0, price_volatility)

    def _calculate_turnover_ratio(self, df: pd.DataFrame) -> float:
        """Calculate asset turnover ratio"""
        # Placeholder - would need volume data
        return 0.6


class SentimentVectorExtractor(BaseFeatureExtractor):
    """Extract sentiment indicators from various data sources"""

    def _process_window(self, data: List[DataPoint]) -> Optional[FeatureVector]:
        """Extract sentiment features"""
        try:
            # Group data by source and signal type
            sentiment_signals = {}
            for dp in data:
                key = f"{dp.source}_{dp.signal_name}"
                if key not in sentiment_signals:
                    sentiment_signals[key] = []
                sentiment_signals[key].append(dp.value)

            # Calculate sentiment components
            market_sentiment = self._calculate_market_sentiment(sentiment_signals)
            news_sentiment = self._calculate_news_sentiment(sentiment_signals)
            social_sentiment = self._calculate_social_sentiment(sentiment_signals)
            volatility_sentiment = self._calculate_volatility_sentiment(sentiment_signals)

            sentiment_vector = np.array(
                [
                    market_sentiment,
                    news_sentiment,
                    social_sentiment,
                    volatility_sentiment,
                    np.mean(
                        [market_sentiment, news_sentiment, social_sentiment, volatility_sentiment]
                    ),
                ]
            )

            confidence = min(0.85, len(sentiment_signals) / 10)

            return FeatureVector(
                vector_type=VectorType.SENTIMENT,
                timestamp=datetime.utcnow(),
                values=sentiment_vector,
                confidence=confidence,
                metadata={
                    "market_sentiment": market_sentiment,
                    "news_sentiment": news_sentiment,
                    "social_sentiment": social_sentiment,
                    "volatility_sentiment": volatility_sentiment,
                },
            )

        except Exception as e:
            logger.error(f"Error extracting sentiment vector: {e}")
            return None

    def _calculate_market_sentiment(self, signals: Dict[str, List[float]]) -> float:
        """Calculate market-based sentiment"""
        # Look for market-related signals
        market_values = []
        for key, values in signals.items():
            if any(term in key.lower() for term in ["market", "index", "equity"]):
                market_values.extend(values)

        if not market_values:
            return 0.5  # Neutral

        # Convert to sentiment scale [-1, 1] -> [0, 1]
        normalized = np.tanh(np.mean(market_values))
        return (normalized + 1) / 2

    def _calculate_news_sentiment(self, signals: Dict[str, List[float]]) -> float:
        """Calculate news-based sentiment"""
        # Placeholder for news sentiment analysis
        return 0.6  # Slightly positive

    def _calculate_social_sentiment(self, signals: Dict[str, List[float]]) -> float:
        """Calculate social media sentiment"""
        # Placeholder for social sentiment analysis
        return 0.5  # Neutral

    def _calculate_volatility_sentiment(self, signals: Dict[str, List[float]]) -> float:
        """Calculate sentiment from volatility patterns"""
        # High volatility often indicates negative sentiment
        volatilities = []
        for values in signals.values():
            if len(values) > 1:
                vol = np.std(values) / (np.mean(np.abs(values)) + 1e-8)
                volatilities.append(vol)

        if not volatilities:
            return 0.5

        avg_vol = np.mean(volatilities)
        # Inverse relationship: higher vol -> lower sentiment
        return 1.0 / (1.0 + avg_vol)


class VolatilityVectorExtractor(BaseFeatureExtractor):
    """Extract volatility patterns and regime indicators"""

    def _process_window(self, data: List[DataPoint]) -> Optional[FeatureVector]:
        """Extract volatility features"""
        try:
            df = self._to_dataframe(data)
            if df.empty:
                return None

            # Volatility components
            realized_vol = self._calculate_realized_volatility(df)
            implied_vol = self._calculate_implied_volatility(df)
            vol_of_vol = self._calculate_volatility_of_volatility(df)
            skewness = self._calculate_skewness(df)
            kurtosis = self._calculate_kurtosis(df)

            volatility_vector = np.array(
                [realized_vol, implied_vol, vol_of_vol, skewness, kurtosis]
            )

            confidence = min(0.9, len(df) / self.window_size)

            return FeatureVector(
                vector_type=VectorType.VOLATILITY,
                timestamp=datetime.utcnow(),
                values=volatility_vector,
                confidence=confidence,
                metadata={
                    "realized_volatility": realized_vol,
                    "implied_volatility": implied_vol,
                    "volatility_of_volatility": vol_of_vol,
                    "skewness": skewness,
                    "kurtosis": kurtosis,
                },
            )

        except Exception as e:
            logger.error(f"Error extracting volatility vector: {e}")
            return None

    def _to_dataframe(self, data: List[DataPoint]) -> pd.DataFrame:
        """Convert to DataFrame"""
        records = []
        for dp in data:
            records.append({"timestamp": dp.timestamp, "signal": dp.signal_name, "value": dp.value})

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        return (
            df.pivot_table(index="timestamp", columns="signal", values="value", aggfunc="mean")
            .fillna(method="ffill")
            .fillna(0)
        )

    def _calculate_realized_volatility(self, df: pd.DataFrame) -> float:
        """Calculate realized volatility across all signals"""
        if df.empty:
            return 0.0

        volatilities = []
        for col in df.columns:
            returns = df[col].pct_change().dropna()
            if len(returns) > 5:
                vol = returns.std()
                volatilities.append(vol if not np.isnan(vol) else 0.0)

        return np.mean(volatilities) if volatilities else 0.0

    def _calculate_implied_volatility(self, df: pd.DataFrame) -> float:
        """Calculate implied volatility (placeholder)"""
        # Would need options data for real implied volatility
        return 0.15  # Placeholder

    def _calculate_volatility_of_volatility(self, df: pd.DataFrame) -> float:
        """Calculate volatility clustering/persistence"""
        if df.empty:
            return 0.0

        vol_of_vols = []
        for col in df.columns:
            returns = df[col].pct_change().dropna()
            if len(returns) > 10:
                rolling_vol = returns.rolling(window=5).std()
                vol_of_vol = rolling_vol.std()
                if not np.isnan(vol_of_vol):
                    vol_of_vols.append(vol_of_vol)

        return np.mean(vol_of_vols) if vol_of_vols else 0.0

    def _calculate_skewness(self, df: pd.DataFrame) -> float:
        """Calculate average skewness across signals"""
        if df.empty:
            return 0.0

        skewness_values = []
        for col in df.columns:
            returns = df[col].pct_change().dropna()
            if len(returns) > 10:
                skew = stats.skew(returns)
                if not np.isnan(skew):
                    skewness_values.append(skew)

        return np.mean(skewness_values) if skewness_values else 0.0

    def _calculate_kurtosis(self, df: pd.DataFrame) -> float:
        """Calculate average kurtosis across signals"""
        if df.empty:
            return 0.0

        kurtosis_values = []
        for col in df.columns:
            returns = df[col].pct_change().dropna()
            if len(returns) > 10:
                kurt = stats.kurtosis(returns)
                if not np.isnan(kurt):
                    kurtosis_values.append(kurt)

        return np.mean(kurtosis_values) if kurtosis_values else 0.0


class FeatureExtractionManager:
    """
    Central manager for all feature extraction operations.
    Coordinates multiple extractors and manages the feature pipeline.
    """

    def __init__(self):
        self.extractors: Dict[VectorType, BaseFeatureExtractor] = {
            VectorType.STRESS: StressVectorExtractor(),
            VectorType.LIQUIDITY: LiquidityVectorExtractor(),
            VectorType.SENTIMENT: SentimentVectorExtractor(),
            VectorType.VOLATILITY: VolatilityVectorExtractor(),
        }

        self.feature_history: Dict[VectorType, List[FeatureVector]] = {
            vector_type: [] for vector_type in VectorType
        }

        self.callbacks: List[callable] = []

    def register_callback(self, callback: callable) -> None:
        """Register callback for new feature vectors"""
        self.callbacks.append(callback)

    def process_data(
        self, data_points: List[DataPoint]
    ) -> Dict[VectorType, Optional[FeatureVector]]:
        """Process new data through all extractors"""
        results = {}

        # Add data to all extractors
        for extractor in self.extractors.values():
            extractor.add_data(data_points)

        # Extract features from each extractor
        for vector_type, extractor in self.extractors.items():
            try:
                feature_vector = extractor.extract_features()
                if feature_vector:
                    # Store in history
                    self.feature_history[vector_type].append(feature_vector)

                    # Trim history to prevent memory growth
                    if len(self.feature_history[vector_type]) > 1000:
                        self.feature_history[vector_type] = self.feature_history[vector_type][
                            -1000:
                        ]

                    # Notify callbacks
                    for callback in self.callbacks:
                        try:
                            callback(feature_vector)
                        except Exception as e:
                            logger.error(f"Feature callback error: {e}")

                results[vector_type] = feature_vector

            except Exception as e:
                logger.error(f"Feature extraction error for {vector_type}: {e}")
                results[vector_type] = None

        return results

    def get_latest_vectors(self) -> Dict[VectorType, Optional[FeatureVector]]:
        """Get the most recent feature vector for each type"""
        latest = {}
        for vector_type, history in self.feature_history.items():
            latest[vector_type] = history[-1] if history else None
        return latest

    def get_vector_history(self, vector_type: VectorType, hours: int = 24) -> List[FeatureVector]:
        """Get historical feature vectors for a specific type"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        history = self.feature_history.get(vector_type, [])
        return [fv for fv in history if fv.timestamp > cutoff_time]


# Global feature extraction manager
feature_manager = FeatureExtractionManager()
