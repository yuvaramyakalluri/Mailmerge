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
    # 1. Run your certificate generation task first
    main()

    # 2. Start HTTP server bound to 0.0.0.0 for Render port detection
    PORT = int(os.environ.get("PORT", 10000))
    Handler = http.server.SimpleHTTPRequestHandler

    # Allow address reuse to prevent address-in-use errors on restarts
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Serving background task status on 0.0.0.0:{PORT}")
        httpd.serve_forever()
