import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime
CHATFILE = "chat.log"
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlparse(self.path).path == "/view":
            try:
                data = open(CHATFILE).read()
            except FileNotFoundError:
                data = ""
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(data.encode())
        else:
            self.send_response(404); self.end_headers()
    def do_POST(self):
        if urlparse(self.path).path == "/append":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode())
            node = payload["node_id"]
            ts = payload["client_time"]
            text = payload["text"]
            with open(CHATFILE, "a") as f:
                f.write(f"{ts} {node}: {text}\n")
            self.send_response(200); self.end_headers()
        else:
            self.send_response(404); self.end_headers()
if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 5000), Handler)
    print("File Server running on port 5000...")
    server.serve_forever()
