#!/usr/bin/env python3
"""
dme.py - Ricart-Agrawala middleware

Usage:
    from dme import DME
    d = DME(node_ip, node_port, peers=[("ip","port","pid"),...], logfile="dme_log.txt")
    d.start()                # starts HTTP server in background
    d.request_cs()           # blocks until allowed
    d.release_cs()           # release and reply deferred
    d.stop()                 # stops HTTP server
"""
import threading, json, urllib.request, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

class DME:
    def __init__(self, my_ip, my_port, peers, logfile=None, timeout=30):
        """
        peers: list of tuples (ip, port, pid_str) where pid_str should be "ip:port"
        my_ip, my_port: strings / ints
        """
        self.my_ip = my_ip
        self.my_port = int(my_port)
        self.node_id = f"{my_ip}:{self.my_port}"
        self.peer_map = [(ip,int(port),pid) for (ip,port,pid) in peers]
        self.peers = [pid for (_,_,pid) in self.peer_map if pid != self.node_id]
        self.LOGFILE = logfile or f"dme_{self.node_id.replace(':','_')}.log"
        self.timeout = timeout

        # RA state
        self.lock = threading.Lock()
        self.logical_clock = 0
        self.request_ts = 0
        self.requesting = False
        self.reply_count = 0
        self.deferred = set()
        self.reply_event = threading.Event()

        self._server = None
        self._server_thread = None
        self._running = False

    # --- Logging & clock ---
    def _log(self, evt, msg=""):
        ts = datetime.now().isoformat()
        s = f"[{evt}] {ts} {self.node_id} {msg}"
        print(s, flush=True)
        with open(self.LOGFILE, "a", encoding="utf-8") as f:
            f.write(s + "\n")

    def _bump_clock(self, incoming=None):
        if incoming is None:
            self.logical_clock += 1
        else:
            # incoming might be int or something else
            try:
                self.logical_clock = max(self.logical_clock, int(incoming)) + 1
            except:
                self.logical_clock += 1
        return self.logical_clock

    # --- HTTP server to receive DME messages ---
    class _Handler(BaseHTTPRequestHandler):
        # handler will access the DME instance via self.server.dme_ref
        def do_POST(self):
            dme = self.server.dme_ref
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
            except:
                self.send_response(400); self.end_headers(); return

            path = urlparse(self.path).path
            if path == "/dme/request":
                sender = data.get("node_id")
                ts = data.get("ts", 0)
                dme._bump_clock(ts)
                dme._log("RECV_REQUEST", f"from={sender} ts={ts} lc={dme.logical_clock}")
                with dme.lock:
                    do_reply = (not dme.requesting) or ((ts, sender) < (dme.request_ts, dme.node_id))
                    if do_reply:
                        threading.Thread(target=dme._send_reply, args=(sender,), daemon=True).start()
                    else:
                        dme.deferred.add(sender)
                        dme._log("DEFER", f"deferred-from={sender}")
                self.send_response(200); self.end_headers()
                return

            if path == "/dme/reply":
                sender = data.get("node_id")
                ts = data.get("ts", 0)
                dme._bump_clock(ts)
                dme._log("RECV_REPLY", f"from={sender} ts={ts} lc={dme.logical_clock}")
                with dme.lock:
                    dme.reply_count += 1
                    if dme.reply_count >= len(dme.peers):
                        dme.reply_event.set()
                self.send_response(200); self.end_headers()
                return

            self.send_response(404); self.end_headers()

        def log_message(self, format, *args):
            # suppress BaseHTTPRequestHandler default logging
            return

    def _send_http(self, ip, port, path, payload):
        url = f"http://{ip}:{port}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.read()
        except Exception as e:
            self._log("NETERR", f"{url} -> {e}")
            return None

    def _send_request_to_peer(self, ip, port, pid):
        payload = {"node_id": self.node_id, "ts": self.request_ts}
        self._send_http(ip, port, "/dme/request", payload)
        self._log("SENT_REQUEST", f"to={pid} ({ip}:{port}) ts={self.request_ts}")

    def _send_reply(self, peer_pid):
        for (ip,port,pid) in self.peer_map:
            if pid == peer_pid:
                payload = {"node_id": self.node_id, "ts": self.logical_clock}
                self._send_http(ip, port, "/dme/reply", payload)
                self._log("SENT_REPLY", f"to={pid} {ip}:{port} lc={self.logical_clock}")
                return
        self._log("SENT_REPLY_FAIL", f"unknown-peer={peer_pid}")

    # --- Public API ---
    def start(self):
        """Start the HTTP server that listens for DME messages."""
        if self._running:
            return
        server = ThreadingHTTPServer(("0.0.0.0", self.my_port), self._Handler)
        server.dme_ref = self
        self._server = server
        self._server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._server_thread.start()
        self._running = True
        self._log("START", f"peers={[p[2] for p in self.peer_map]} file_server_placeholder")
        return

    def stop(self):
        if self._server:
            self._server.shutdown()
        self._running = False
        self._log("STOP", "shutting down")

    def request_cs(self, timeout=None):
        """
        Block until receiving REPLY from all peers or timeout (seconds).
        Returns True if entered CS (even after timeout), False on error.
        """
        with self.lock:
            self.requesting = True
            self.request_ts = self._bump_clock()
            self.reply_count = 0
            self.reply_event.clear()

        # send requests
        for (ip,port,pid) in self.peer_map:
            if pid == self.node_id:
                continue
            threading.Thread(target=self._send_request_to_peer, args=(ip,port,pid), daemon=True).start()

        self._log("REQUEST", f"ts={self.request_ts} peers={[p[2] for p in self.peer_map if p[2]!=self.node_id]}")
        timed_out = not self.reply_event.wait(timeout if timeout is not None else self.timeout)
        if timed_out:
            self._log("TIMEOUT", f"did not receive all replies in {timeout or self.timeout}s, reply_count={self.reply_count}")
        self._log("ENTER", f"ts={self.request_ts}")
        return True

    def release_cs(self):
        with self.lock:
            self.requesting = False
            to_send = list(self.deferred)
            self.deferred.clear()
        for peer_pid in to_send:
            self._send_reply(peer_pid)
        self._log("EXIT", f"released and replied to deferred: {to_send}")

    # Convenience/helper to send a reply to a specific peer (public)
    def send_reply_to(self, peer_pid):
        self._send_reply(peer_pid)
