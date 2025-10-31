"""
N³ MONITORING DASHBOARD LAUNCHER
================================
Launch all monitoring and analytics dashboards

This script starts:
1. N³ Analytics Dashboard (performance metrics)
2. N³ Live Dashboard (real-time trading)
3. WebSocket Server (real-time data streaming)
"""

import asyncio
import subprocess
import sys
import time
import logging
from pathlib import Path
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print monitoring banner"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*70}")
    print(f" N³ MONITORING DASHBOARD LAUNCHER")
    print(f"{'='*70}{Style.RESET_ALL}\n")


def launch_analytics_dashboard():
    """Launch N³ Analytics Dashboard"""
    print(f"{Fore.CYAN}📊 Launching Analytics Dashboard...{Style.RESET_ALL}")
    
    try:
        process = subprocess.Popen(
            [sys.executable, "n3_analytics_dashboard.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        
        time.sleep(2)
        
        if process.poll() is None:
            print(f"{Fore.GREEN}✅ Analytics Dashboard started (PID: {process.pid}){Style.RESET_ALL}")
            print(f"   URL: http://localhost:8050")
            return process
        else:
            print(f"{Fore.RED}❌ Analytics Dashboard failed to start{Style.RESET_ALL}")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}❌ Error launching Analytics Dashboard: {e}{Style.RESET_ALL}")
        return None


def launch_live_dashboard():
    """Launch N³ Live Dashboard"""
    print(f"{Fore.CYAN}📈 Launching Live Dashboard...{Style.RESET_ALL}")
    
    try:
        process = subprocess.Popen(
            [sys.executable, "n3_live_dashboard.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        
        time.sleep(2)
        
        if process.poll() is None:
            print(f"{Fore.GREEN}✅ Live Dashboard started (PID: {process.pid}){Style.RESET_ALL}")
            print(f"   URL: http://localhost:8051")
            return process
        else:
            print(f"{Fore.RED}❌ Live Dashboard failed to start{Style.RESET_ALL}")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}❌ Error launching Live Dashboard: {e}{Style.RESET_ALL}")
        return None


def launch_websocket_server():
    """Launch WebSocket Server"""
    print(f"{Fore.CYAN}🔌 Launching WebSocket Server...{Style.RESET_ALL}")
    
    try:
        process = subprocess.Popen(
            [sys.executable, "websocket_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        
        time.sleep(2)
        
        if process.poll() is None:
            print(f"{Fore.GREEN}✅ WebSocket Server started (PID: {process.pid}){Style.RESET_ALL}")
            print(f"   URL: ws://localhost:8765")
            return process
        else:
            print(f"{Fore.RED}❌ WebSocket Server failed to start{Style.RESET_ALL}")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}❌ Error launching WebSocket Server: {e}{Style.RESET_ALL}")
        return None


def main():
    """Main launcher function"""
    print_banner()
    
    processes = []
    
    # Launch WebSocket Server first
    ws_process = launch_websocket_server()
    if ws_process:
        processes.append(('WebSocket Server', ws_process))
    print()
    
    # Launch Analytics Dashboard
    analytics_process = launch_analytics_dashboard()
    if analytics_process:
        processes.append(('Analytics Dashboard', analytics_process))
    print()
    
    # Launch Live Dashboard
    live_process = launch_live_dashboard()
    if live_process:
        processes.append(('Live Dashboard', live_process))
    print()
    
    # Summary
    print(f"{Fore.GREEN}{Style.BRIGHT}{'='*70}")
    print(f" MONITORING DASHBOARDS ACTIVE")
    print(f"{'='*70}{Style.RESET_ALL}\n")
    
    if processes:
        print(f"{Fore.YELLOW}Active Services:{Style.RESET_ALL}")
        for name, proc in processes:
            print(f"   ✅ {name} (PID: {proc.pid})")
        print()
        
        print(f"{Fore.CYAN}Dashboard URLs:{Style.RESET_ALL}")
        if analytics_process:
            print(f"   📊 Analytics: http://localhost:8050")
        if live_process:
            print(f"   📈 Live Trading: http://localhost:8051")
        if ws_process:
            print(f"   🔌 WebSocket: ws://localhost:8765")
        print()
        
        print(f"{Fore.YELLOW}Press Ctrl+C to stop all dashboards...{Style.RESET_ALL}\n")
        
        try:
            # Keep running until interrupted
            while True:
                time.sleep(1)
                
                # Check if any process died
                for name, proc in processes:
                    if proc.poll() is not None:
                        print(f"{Fore.RED}⚠️  {name} stopped unexpectedly{Style.RESET_ALL}")
                        processes.remove((name, proc))
                
                if not processes:
                    print(f"{Fore.RED}All processes stopped{Style.RESET_ALL}")
                    break
                    
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Stopping all dashboards...{Style.RESET_ALL}")
            
            for name, proc in processes:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    print(f"{Fore.GREEN}✅ {name} stopped{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}❌ Error stopping {name}: {e}{Style.RESET_ALL}")
                    try:
                        proc.kill()
                    except:
                        pass
            
            print(f"\n{Fore.GREEN}All dashboards stopped{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ No dashboards were started successfully{Style.RESET_ALL}")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.exception("Launcher error")
        sys.exit(1)

