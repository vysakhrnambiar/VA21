#!/usr/bin/env python3
import subprocess
import time
import os
import signal
import sys
import logging
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from queue import Queue, Empty

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("ProcessManager")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)
logger.addHandler(console_handler)

# File handler with rotation
log_file_path = os.path.join(log_dir, "process_manager.log")
file_handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=5)  # 5MB per file, keep 5 backups
file_handler.setLevel(logging.INFO)
file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_format)
logger.addHandler(file_handler)

# Global process variables
web_server_process = None
calling_agent_process = None
processes = {}

# Configuration
CHECK_INTERVAL = 5  # seconds between checks
MAX_RESTART_ATTEMPTS = 5  # maximum restart attempts per process before waiting longer
RESTART_COOLDOWN = 60  # seconds to wait after max restart attempts
restart_counts = {"web_server": 0, "calling_agent": 0}
restart_cooldown_until = {"web_server": 0, "calling_agent": 0}

# This script should be run inside the project's virtual environment
# where all dependencies are already installed

# Stream reader for capturing output
class StreamReader(threading.Thread):
    def __init__(self, stream, name, is_error=False):
        threading.Thread.__init__(self)
        self.stream = stream
        self.name = name
        self.is_error = is_error
        self.daemon = True  # Thread will exit when main thread exits
        self.start()
    
    def run(self):
        while True:
            line = self.stream.readline()
            if not line:
                break
            line = line.strip()
            if line:
                if self.is_error:
                    logger.warning(f"[{self.name}] ERROR: {line}")
                else:
                    logger.info(f"[{self.name}] {line}")

def start_process(name, script_path):
    """Generic function to start a process"""
    logger.info(f"Starting {name}...")
    try:
        # Use Python executable from current environment
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        logger.info(f"{name} started with PID {process.pid}")
        
        # Set up readers to capture output
        StreamReader(process.stdout, name, is_error=False)
        StreamReader(process.stderr, name, is_error=True)
        
        processes[name] = process
        return process
    except Exception as e:
        logger.error(f"Failed to start {name}: {e}")
        return None

def start_web_server():
    """Start the web server process"""
    return start_process("web_server", "web_server.py")

def start_calling_agent():
    """Start the calling agent process"""
    return start_process("calling_agent", "calling_agent.py")

def check_process(name, process):
    """Check if process is still running"""
    if process is None:
        return False
    
    # Check if process is still running
    return process.poll() is None

# The monitor_output function has been removed since we're using StreamReader threads
# to handle process output capture in a more reliable way.

def restart_process(name):
    """Restart a process that has crashed"""
    current_time = time.time()
    
    # Check if we're in a cooldown period
    if current_time < restart_cooldown_until[name]:
        cooldown_remaining = int(restart_cooldown_until[name] - current_time)
        logger.warning(f"{name} crashed but in cooldown period. Waiting {cooldown_remaining}s before restart attempt.")
        return None
    
    # Increment restart counter
    restart_counts[name] += 1
    
    # Check if we've hit max restart attempts
    if restart_counts[name] > MAX_RESTART_ATTEMPTS:
        logger.warning(f"{name} crashed and has been restarted {restart_counts[name]} times. Entering cooldown.")
        restart_cooldown_until[name] = current_time + RESTART_COOLDOWN
        restart_counts[name] = 0  # Reset counter
        return None
    
    logger.warning(f"{name} crashed. Restarting (attempt {restart_counts[name]})...")
    
    # Kill the old process if it's somehow still running
    old_process = processes.get(name)
    if old_process and old_process.poll() is None:
        try:
            old_process.terminate()
            # Give it a moment to terminate
            time.sleep(2)
            # Force kill if still running
            if old_process.poll() is None:
                old_process.kill()
        except Exception as e:
            logger.error(f"Error terminating old {name} process: {e}")
    
    # Start the appropriate process
    if name == "web_server":
        return start_web_server()
    elif name == "calling_agent":
        return start_calling_agent()
    return None

def shutdown_all():
    """Gracefully shut down all processes"""
    logger.info("Shutting down all processes...")
    
    for name, process in processes.items():
        if process and process.poll() is None:
            logger.info(f"Terminating {name}...")
            try:
                process.terminate()
                # Give it some time to terminate gracefully
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"{name} did not terminate gracefully, killing...")
                process.kill()
            except Exception as e:
                logger.error(f"Error shutting down {name}: {e}")
    
    logger.info("All processes shut down.")

def main():
    """Main function to start and monitor processes"""
    logger.info("==== Process Manager Started ====")
    
    # Start processes
    web_server_process = start_web_server()
    time.sleep(2)  # Wait briefly between starting processes
    calling_agent_process = start_calling_agent()
    
    try:
        while True:
            # Check web server
            if not check_process("web_server", processes.get("web_server")):
                if processes.get("web_server"):
                    logger.warning("Web server has stopped running!")
                processes["web_server"] = restart_process("web_server")
            else:
                # Reset restart count if it's been running for a while
                if restart_counts["web_server"] > 0 and time.time() - restart_cooldown_until["web_server"] > 300:
                    restart_counts["web_server"] = 0
                    logger.info("Web server has been stable for a while. Resetting restart counter.")
                
                # No need to call monitor_output as StreamReader threads handle this
            
            # Check calling agent
            if not check_process("calling_agent", processes.get("calling_agent")):
                if processes.get("calling_agent"):
                    logger.warning("Calling agent has stopped running!")
                processes["calling_agent"] = restart_process("calling_agent")
            else:
                # Reset restart count if it's been running for a while
                if restart_counts["calling_agent"] > 0 and time.time() - restart_cooldown_until["calling_agent"] > 300:
                    restart_counts["calling_agent"] = 0
                    logger.info("Calling agent has been stable for a while. Resetting restart counter.")
                
                # No need to call monitor_output as StreamReader threads handle this
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("Process Manager shutting down due to KeyboardInterrupt.")
    except Exception as e:
        logger.error(f"Process Manager encountered an error: {e}", exc_info=True)
    finally:
        shutdown_all()
        logger.info("==== Process Manager Stopped ====")

if __name__ == "__main__":
    main()