#!/usr/bin/python3
"""
Plane Tracker RGB Pi - Main Entry Point

This script initializes and runs the plane tracking display system.
It starts a Flask web server for the web interface and runs the main
LED matrix display loop to show overhead flight information.

The script handles graceful shutdown via SIGTERM and SIGINT signals,
ensuring the Flask subprocess is properly terminated on exit.
"""

import logging
import os
import signal
import subprocess
import sys

from display import Display

# Global reference to Flask subprocess for cleanup
flask_process = None
display = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """Handle shutdown signals for graceful termination."""
    sig_name = signal.Signals(signum).name
    logger.info(f"Received {sig_name}, initiating graceful shutdown...")
    cleanup()
    sys.exit(0)


def cleanup():
    """Clean up resources before exit."""
    global flask_process, display

    if flask_process is not None:
        logger.info("Terminating Flask web server...")
        try:
            flask_process.terminate()
            flask_process.wait(timeout=5)
            logger.info("Flask web server terminated successfully")
        except subprocess.TimeoutExpired:
            logger.warning("Flask server did not terminate gracefully, forcing kill...")
            flask_process.kill()
        except Exception as e:
            logger.error(f"Error terminating Flask server: {e}")

    if display is not None:
        logger.info("Stopping display...")
        # Display cleanup if needed


def main():
    """Main entry point for the plane tracker application."""
    global flask_process, display

    # Get directory of this script (its-a-plane.py)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Change working directory to script's directory to fix relative path issues
    os.chdir(base_dir)
    logger.info(f"Working directory set to: {base_dir}")

    # Build path to web/app.py
    app_path = os.path.join(base_dir, "web", "app.py")

    # Start Flask server in background
    logger.info(f"Starting Flask web server from: {app_path}")
    flask_process = subprocess.Popen(
        ["python3", app_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    logger.info(f"Flask web server started with PID: {flask_process.pid}")

    # Start display loop
    logger.info("Initializing LED matrix display...")
    display = Display()
    logger.info("Starting display loop...")
    display.run()


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        main()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        cleanup()
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error in main: {e}")
        cleanup()
    sys.exit(1)
