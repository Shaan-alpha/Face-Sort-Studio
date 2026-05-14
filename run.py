"""
Face Sort Studio — Entry Point (System Tray Edition)
====================================================
This entry point handles the Flask server and a System Tray icon.
"""

import os
import threading
import webbrowser
import sys
from pathlib import Path
import pystray
from PIL import Image, ImageDraw
from face_sort.app.main import create_app

# Initialize Flask app
app = create_app()

def create_tray_icon():
    """Creates a simple icon for the system tray using Pillow."""
    # Create a 64x64 image with a blue background and a white 'F'
    width = 64
    height = 64
    color1 = (59, 130, 246)  # Blue
    color2 = (255, 255, 255) # White
    
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    # Simple representation of a face/sorting
    dc.ellipse([10, 10, 54, 54], outline=color2, width=4)
    dc.rectangle([25, 25, 39, 39], fill=color2)
    
    return image

def on_open_browser(icon, item):
    """Opens the app in the default browser."""
    webbrowser.open("http://127.0.0.1:8000")

def on_quit(icon, item):
    """Stops the icon and exits the entire application."""
    icon.stop()
    os._exit(0) # Force exit all threads

def start_flask():
    """Runs the Flask server."""
    host = os.environ.get("FACE_SORT_HOST", "127.0.0.1")
    port = int(os.environ.get("FACE_SORT_PORT", "8000"))
    # Disable reloader because it conflicts with threading/tray
    app.run(host=host, port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    # 1. Start Flask in a background thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    # 2. Open browser automatically on start
    webbrowser.open("http://127.0.0.1:8000")
    
    # 3. Setup and Run the System Tray Icon (Main Thread)
    menu = pystray.Menu(
        pystray.MenuItem("Open Studio", on_open_browser, default=True),
        pystray.MenuItem("Exit Studio", on_quit)
    )
    
    icon = pystray.Icon(
        "FaceSortStudio",
        create_tray_icon(),
        "Face Sort Studio",
        menu
    )
    
    print("Face Sort Studio is running in the system tray.")
    icon.run()
