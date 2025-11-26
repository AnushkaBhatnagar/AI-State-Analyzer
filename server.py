#!/usr/bin/env python3
"""
Auto-start local server for AI State Analyzer
Opens both index.html and index_with_panel.html automatically in the browser
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path
import time
import threading

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler with improved logging"""
    
    def log_message(self, format, *args):
        """Override to provide cleaner log messages"""
        print(f"[{self.log_date_time_string()}] {format % args}")

def open_browsers():
    """Open both HTML files in the browser after a short delay"""
    time.sleep(1.5)  # Wait for server to fully start
    
    print("\n" + "="*60)
    print("Opening browser windows...")
    print("="*60)
    
    # Open index.html
    url1 = f"http://localhost:{PORT}/index.html"
    print(f"Opening: {url1}")
    webbrowser.open(url1)
    
    time.sleep(0.5)  # Small delay between opens
    
    # Open index_with_panel.html
    url2 = f"http://localhost:{PORT}/index_with_panel.html"
    print(f"Opening: {url2}")
    webbrowser.open(url2)
    
    print("\n" + "="*60)
    print("Both files opened in your browser!")
    print("="*60)

def main():
    """Start the local HTTP server and open browser windows"""
    
    # Check if we're in the right directory
    current_dir = Path.cwd()
    index_file = current_dir / "index.html"
    panel_file = current_dir / "index_with_panel.html"
    
    if not index_file.exists():
        print("[ERROR] index.html not found in current directory")
        print(f"        Current directory: {current_dir}")
        sys.exit(1)
    
    if not panel_file.exists():
        print("[WARNING] index_with_panel.html not found")
        print("          Run 'python panel_generator.py' to generate it")
        print()
    
    # Start server
    os.chdir(current_dir)
    
    Handler = MyHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print("\n" + "="*60)
            print("AI STATE ANALYZER - LOCAL SERVER")
            print("="*60)
            print(f"Server running at: http://localhost:{PORT}/")
            print(f"Serving directory: {current_dir}")
            print()
            print("Available files:")
            print(f"  • http://localhost:{PORT}/index.html")
            print(f"  • http://localhost:{PORT}/index_with_panel.html")
            print()
            print("="*60)
            print("Press Ctrl+C to stop the server")
            print("="*60 + "\n")
            
            # Open browsers in a separate thread
            browser_thread = threading.Thread(target=open_browsers, daemon=True)
            browser_thread.start()
            
            # Start serving
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("Server stopped by user")
        print("="*60)
        sys.exit(0)
    except OSError as e:
        if e.errno == 48 or e.errno == 10048:  # Address already in use
            print(f"\n[ERROR] Port {PORT} is already in use!")
            print(f"        Try closing other applications or use a different port")
            sys.exit(1)
        else:
            raise

if __name__ == "__main__":
    main()
