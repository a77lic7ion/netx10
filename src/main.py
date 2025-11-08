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


def main():
    """Main application entry point"""
    try:
        # Fallback file tracing in case console output is suppressed
        trace_path = src_path / "logs" / "startup_trace.txt"
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write("[main] Starting application...\n")
        except Exception:
            pass

        print("Importing dependencies...")
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write("[main] Importing dependencies...\n")
        except Exception:
            pass
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from qasync import QEventLoop
        from core.application import NetworkSwitchAIApp
        from core.config import AppConfig
        from utils.logging_utils import setup_logging
        print("Dependencies imported.")
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write("[main] Dependencies imported.\n")
        except Exception:
            pass
        # Setup logging
        print("Setting up logging...")
        setup_logging()
        print("Logging setup complete.")
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write("[main] Logging setup complete.\n")
        except Exception:
            pass
        
        # Create QApplication
        print("Creating QApplication...")
        app = QApplication(sys.argv)
        app.setApplicationName("NetworkSwitch AI Assistant")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("NetIntelliX")
        print("QApplication created.")
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write("[main] QApplication created.\n")
        except Exception:
            pass
        
        # Set application style
        app.setStyle("Fusion")
        
        # Create event loop
        print("Creating event loop...")
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)
        print("Event loop created.")
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write("[main] Event loop created.\n")
        except Exception:
            pass
        
        # Create and show main window
        print("Creating main window...")
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write("[main] Creating main window...\n")
        except Exception:
            pass
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write("[main] Instantiating AppConfig...\n")
        except Exception:
            pass
        config = AppConfig()
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write("[main] AppConfig instantiated. Creating NetworkSwitchAIApp...\n")
        except Exception:
            pass
        main_window = NetworkSwitchAIApp(config)
        print("Main window created.")
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write("[main] Main window created.\n")
        except Exception:
            pass
        main_window.show()
        print("Main window shown.")
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write("[main] Main window shown.\n")
        except Exception:
            pass
        
        # Run the application
        with loop:
            loop.run_forever()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        try:
            with open(trace_path, "a", encoding="utf-8") as f:
                f.write(f"[main] Error: {e}\n")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":


    main()
