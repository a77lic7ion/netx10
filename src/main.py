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
    
    # Setup logging
    setup_logging()
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("NetworkSwitch AI Assistant")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("NetIntelliX")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create event loop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create and show main window
    config = AppConfig()
    main_window = NetworkSwitchAIApp(config)
    main_window.show()
    
    # Run the application
    with loop:
        loop.run_forever()


if __name__ == "__main__":


    main()