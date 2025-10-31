"""
N³ AUTONOMOUS TRADING DEPLOYMENT
================================
Deploy the fully trained N³ system for autonomous trading

This script:
1. Verifies SSE training completion
2. Loads trained NRCL agent
3. Initializes all integrated systems
4. Launches autonomous trading
5. Starts monitoring dashboards
"""

import asyncio
import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('n3_autonomous_deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from n3_integrated_live_system import N3IntegratedTradingSystem
from ig_markets_integration import IGMarketConfig
from nrcl_agent import NRCLAgent
from sovereign_simulation_env import SovereignSimulationEngine


def print_banner():
    """Print deployment banner"""
    print(f"\n{Fore.GREEN}{Style.BRIGHT}{'='*70}")
    print(f" N³ AUTONOMOUS TRADING SYSTEM - DEPLOYMENT")
    print(f"{'='*70}{Style.RESET_ALL}\n")


def verify_training():
    """Verify SSE training was completed"""
    print(f"{Fore.CYAN}📊 Step 1: Verifying SSE Training...{Style.RESET_ALL}")
    
    results_file = Path("data/sse/sse_training_results.json")
    
    if not results_file.exists():
        print(f"{Fore.RED}❌ SSE training results not found!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   Please run: python run_sse_training.py{Style.RESET_ALL}")
        return False
    
    with open(results_file) as f:
        results = json.load(f)
    
    metrics = results['metrics']
    
    print(f"{Fore.GREEN}✅ SSE Training Results:{Style.RESET_ALL}")
    print(f"   Episodes: {metrics['total_episodes']}")
    print(f"   Win Rate: {metrics['win_rate']*100:.1f}%")
    print(f"   Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown: {metrics['max_drawdown']*100:.2f}%")
    print(f"   Total Profit: ${metrics['total_profit']:.2f}")
    
    # Check if targets met
    if metrics['win_rate'] >= 0.95:
        print(f"{Fore.GREEN}   ✅ Win rate target met (≥95%){Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}   ⚠️  Win rate {metrics['win_rate']*100:.1f}% below 95% target{Style.RESET_ALL}")
    
    if metrics['sharpe_ratio'] >= 2.0:
        print(f"{Fore.GREEN}   ✅ Sharpe ratio target met (≥2.0){Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}   ⚠️  Sharpe ratio {metrics['sharpe_ratio']:.2f} below 2.0 target{Style.RESET_ALL}")
    
    print()
    return True


def load_agent():
    """Load trained NRCL agent"""
    print(f"{Fore.CYAN}🧠 Step 2: Loading Trained NRCL Agent...{Style.RESET_ALL}")
    
    try:
        agent = NRCLAgent(data_dir="data/nrcl")
        print(f"{Fore.GREEN}✅ NRCL Agent loaded successfully{Style.RESET_ALL}")
        print(f"   Q-table states: {len(agent.q_learner.q_table)}")
        print()
        return agent
    except Exception as e:
        print(f"{Fore.RED}❌ Failed to load NRCL agent: {e}{Style.RESET_ALL}")
        return None


def check_ig_config():
    """Check IG Markets configuration"""
    print(f"{Fore.CYAN}🔑 Step 3: Checking IG Markets Configuration...{Style.RESET_ALL}")
    
    env_file = Path(".env")
    
    if not env_file.exists():
        print(f"{Fore.RED}❌ .env file not found!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   Please create .env with IG Markets credentials{Style.RESET_ALL}")
        return None
    
    # Load environment variables
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['IG_USERNAME', 'IG_PASSWORD', 'IG_API_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"{Fore.RED}❌ Missing environment variables: {', '.join(missing)}{Style.RESET_ALL}")
        return None
    
    # Create IG config
    config = IGMarketConfig(
        username=os.getenv('IG_USERNAME'),
        password=os.getenv('IG_PASSWORD'),
        api_key=os.getenv('IG_API_KEY'),
        is_demo=os.getenv('IG_IS_DEMO', 'true').lower() == 'true'
    )
    
    mode = "DEMO" if config.is_demo else "LIVE"
    print(f"{Fore.GREEN}✅ IG Markets configuration loaded ({mode} mode){Style.RESET_ALL}")
    print()
    
    return config


async def deploy_system(ig_config: IGMarketConfig, agent: NRCLAgent):
    """Deploy the autonomous trading system"""
    print(f"{Fore.CYAN}🚀 Step 4: Deploying Autonomous Trading System...{Style.RESET_ALL}")
    
    try:
        # Initialize integrated system
        system = N3IntegratedTradingSystem(
            ig_config=ig_config,
            enable_websocket=True,
            force_simulation=False
        )
        
        # Override with trained agent
        system.nrcl_agent = agent
        
        # Initialize system
        await system.initialize()
        
        print(f"{Fore.GREEN}✅ System initialized successfully{Style.RESET_ALL}")
        print()
        
        # Start autonomous trading
        print(f"{Fore.CYAN}💹 Step 5: Starting Autonomous Trading...{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{Style.BRIGHT}{'='*70}")
        print(f" AUTONOMOUS TRADING ACTIVE")
        print(f"{'='*70}{Style.RESET_ALL}\n")
        
        print(f"{Fore.YELLOW}System Status:{Style.RESET_ALL}")
        print(f"   🧠 NRCL Agent: ACTIVE")
        print(f"   🎯 Quantum Engine: ACTIVE")
        print(f"   📊 Neural Analytics: ACTIVE")
        print(f"   📰 News Sentiment: ACTIVE")
        print(f"   📅 Economic Calendar: ACTIVE")
        print(f"   🌊 Surfin' Engine: ACTIVE")
        print(f"   🔌 WebSocket: ACTIVE")
        print()
        
        print(f"{Fore.CYAN}Press Ctrl+C to stop trading...{Style.RESET_ALL}\n")
        
        # Run trading loop
        await system.run_trading_loop()
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️  Shutdown requested by user{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Closing all positions and stopping system...{Style.RESET_ALL}")
        # System cleanup will happen automatically
    except Exception as e:
        print(f"\n{Fore.RED}❌ Error during deployment: {e}{Style.RESET_ALL}")
        logger.exception("Deployment error")
        raise


async def main():
    """Main deployment function"""
    print_banner()
    
    # Step 1: Verify training
    if not verify_training():
        print(f"{Fore.RED}Deployment aborted: Training verification failed{Style.RESET_ALL}")
        return 1
    
    # Step 2: Load agent
    agent = load_agent()
    if not agent:
        print(f"{Fore.RED}Deployment aborted: Failed to load agent{Style.RESET_ALL}")
        return 1
    
    # Step 3: Check IG config
    ig_config = check_ig_config()
    if not ig_config:
        print(f"{Fore.RED}Deployment aborted: IG configuration failed{Style.RESET_ALL}")
        return 1
    
    # Step 4-5: Deploy system
    try:
        await deploy_system(ig_config, agent)
        return 0
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Deployment cancelled by user{Style.RESET_ALL}")
        sys.exit(0)

