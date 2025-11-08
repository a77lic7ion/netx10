#!/usr/bin/env python3
"""
NetworkSwitch AI Assistant - Main Application Entry Point
"""

import sys
import asyncio
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path.parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from qasync import QEventLoop

from core.application import NetworkSwitchAIApp
from core.config import AppConfig
from utils.logging import setup_logging


def main():
    """Main application entry point"""
    try:
        # Setup logging
        print("Setting up logging...")
        setup_logging()
        print("Logging setup complete.")
        
        # Create QApplication
        print("Creating QApplication...")
        app = QApplication(sys.argv)
        app.setApplicationName("NetworkSwitch AI Assistant")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("NetIntelliX")
        print("QApplication created.")
        
        # Set application style
        app.setStyle("Fusion")
        
        # Create event loop
        print("Creating event loop...")
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)
        print("Event loop created.")
        
        # Create and show main window
        print("Creating main window...")
        config = AppConfig()
        main_window = NetworkSwitchAIApp(config)
        print("Main window created.")
        main_window.show()
        print("Main window shown.")
        
        # Run the application
        with loop:
            loop.run_forever()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":


    main()