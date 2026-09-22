"""Root entrypoint to run the Certificate Generation Agent directly.

Usage:
    python main.py
    python main.py --help
"""
import http.server
import os
import socketserver

from certificate_agent.main import main

if __name__ == "__main__":
    main()

    # --- KEEP FREE RENDER WEB SERVICE ONLINE ---
    PORT = int(os.environ.get("PORT", 10000))
    Handler = http.server.SimpleHTTPRequestHandler

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving background task status on port {PORT}")
        httpd.serve_forever()
