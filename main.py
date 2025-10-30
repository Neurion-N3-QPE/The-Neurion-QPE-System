"""
Neurion QPE System - Main Entry Point
The ultimate N3 trading system
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

from core.integrity import IntegrityBus
from trading.autonomous_trader_v2 import AutonomousTraderV2
from config.settings import load_config
from core.execution.order_executor import OrderExecutor
from integrations.ig_markets_api import IGMarketsAPI


# Setup logging
# Fix Windows encoding for emojis
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,  # Changed to INFO for cleaner output
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'data/logs/neurion_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point"""
    logger.info("="*80)
    logger.info("🚀 NEURION QPE SYSTEM V3.0")
    logger.info("="*80)
    
    try:
        # Load configuration
        config = load_config()
        logger.info(f"✅ Configuration loaded: {config.get('profile', 'default')}")
        
        # Initialize trader
        trader = AutonomousTraderV2(config)
        await trader.initialize()
        
        # Start trading
        logger.info("\n" + "="*80)
        logger.info("🎯 STARTING AUTONOMOUS TRADING")
        logger.info("="*80 + "\n")
        
        await trader.start()
        
        ig_api = IGMarketsAPI(
            api_key="your_api_key",
            username="your_username",
            password="your_password",
            account_id="your_account_id",
            demo=False
        )

        await ig_api.initialize()

        executor = OrderExecutor(ig_api)

        # Example trade execution
        trade_response = await executor.execute_trade(
            epic="IX.D.SPTRD.DAILY.IP",
            direction="SELL",
            size=0.3,
            agent="EchoQuant"
        )

        print(trade_response)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Shutdown signal received")
        await trader.stop()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        logger.info("\n" + "="*80)
        logger.info("🏁 NEURION QPE SYSTEM STOPPED")
        logger.info("="*80)
        # Ensure API sessions are closed cleanly
        try:
            if 'ig_api' in locals() and ig_api is not None:
                await ig_api.shutdown()
        except Exception:
            logger.debug("Error shutting down IG API session", exc_info=True)


if __name__ == "__main__":
    # Create necessary directories
    Path("data/logs").mkdir(parents=True, exist_ok=True)
    Path("data/checkpoints").mkdir(parents=True, exist_ok=True)
    Path("data/market_data").mkdir(parents=True, exist_ok=True)
    
    # Run main
    asyncio.run(main())
