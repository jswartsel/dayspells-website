#!/usr/bin/env python3
"""Dev server. Serves the repo root, where index.html lives.

    python tools/serve.py        ->  http://localhost:8000/
"""
import http.server, socketserver, os, functools, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, max-age=0')
        super().end_headers()


if __name__ == '__main__':
    handler = functools.partial(NoCache, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('', PORT), handler) as httpd:
        print(f'serving {ROOT}\n  ->  http://localhost:{PORT}/')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
