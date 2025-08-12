#!/usr/bin/env python3
"""
Simple web server to serve the roof viewer application locally.
This allows the HTML file to access the CSV data via AJAX.
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

def main():
    # Change to the script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    port = 8000
    
    # Try to find an available port
    for port_try in range(8000, 8100):
        try:
            with socketserver.TCPServer(("", port_try), http.server.SimpleHTTPRequestHandler) as httpd:
                port = port_try
                break
        except OSError:
            continue
    
    try:
        with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
            url = f"http://localhost:{port}/roof_viewer.html"
            
            print(f"🌐 Starting web server at {url}")
            print(f"📁 Serving files from: {script_dir}")
            print(f"🔗 Opening browser automatically...")
            print(f"⏹️  Press Ctrl+C to stop the server")
            
            # Open browser automatically
            webbrowser.open(url)
            
            # Start serving
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
