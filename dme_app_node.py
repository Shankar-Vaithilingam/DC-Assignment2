import sys, threading, argparse, time, json, urllib.request, os
from dme import DME
from datetime import datetime

def call_file_server_append(fs_ip, fs_port, node_id, text):
    payload = {"node_id": node_id, "client_time": datetime.now().isoformat(), "text": text}
    url = f"http://{fs_ip}:{fs_port}/append"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return f"ERROR: {e}"
def call_file_server_view(fs_ip, fs_port):
    url = f"http://{fs_ip}:{fs_port}/view"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return f"ERROR: {e}"
def run_cli(dme, file_server, autopost=None, autopost_file=None, delay=1.0):
    print("Commands: view | post <text> | quit")
    if autopost is not None or autopost_file is not None:
        def ap():
            time.sleep(delay)
            if autopost_file:
                try:
                    with open(autopost_file, "r", encoding="utf-8", errors="ignore") as fh:
                        text = fh.read()
                except Exception as e:
                    print("AUTOPOST-FILE read error:", e)
                    return
            else:
                text = autopost
            print(f"[AUTOPOST] Posting {('file:'+autopost_file) if autopost_file else ('text of len '+str(len(text)))}")
            dme.request_cs()
            try:
                r = call_file_server_append(file_server[0], file_server[1], dme.node_id, text)
                dme._log("POST", f"to_file_server autopost result={r} len={len(text)}")
            finally:
                dme.release_cs()
        threading.Thread(target=ap, daemon=True).start()
    while True:
        try:
            raw = input("> ").strip()
        except EOFError:
            break
        if not raw: continue
        if raw == "quit":
            break
        if raw == "view":
            out = call_file_server_view(file_server[0], file_server[1])
            print("----- CHAT LOG -----")
            print(out)
            print("--------------------")
            continue
        if raw.startswith("post "):
            text = raw[5:].strip()
            dme._log("CLI_POST", f"requesting CS to post: {text[:80]}{'...' if len(text)>80 else ''}")
            dme.request_cs()
            try:
                r = call_file_server_append(file_server[0], file_server[1], dme.node_id, text)
                dme._log("POST", f"to_file_server result={r} text_len={len(text)}")
            finally:
                dme.release_cs()
            continue
        print("Unknown cmd")
def parse_peer(s):
    ip,port = s.split(":")
    pid = f"{ip}:{port}"
    return (ip, int(port), pid)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("my_ip")
    parser.add_argument("my_port", type=int)
    parser.add_argument("peer1")
    parser.add_argument("peer2")
    parser.add_argument("file_server")
    parser.add_argument("--autopost", type=str, help="text to autopost (optional)")
    parser.add_argument("--autopost-file", type=str, help="path to file whose contents will be autoposted")
    parser.add_argument("--delay", type=float, default=1.0, help="delay before autopost")
    args = parser.parse_args()
    fs_parts = args.file_server.split(":")
    file_server = (fs_parts[0], int(fs_parts[1]))
    raw_peers = [parse_peer(args.peer1), parse_peer(args.peer2)]
    peers = []
    for ip,port,pid in raw_peers:
        if (ip,port) == file_server: continue
        if pid == f"{args.my_ip}:{args.my_port}": continue
        if pid not in [p[2] for p in peers]:
            peers.append((ip,port,pid))
    dme = DME(args.my_ip, args.my_port, peers, logfile=f"dme_{args.my_ip.replace('.','_')}_{args.my_port}.log")
    dme.start()
    try:
        run_cli(dme, file_server, autopost=args.autopost, autopost_file=args.autopost_file, delay=args.delay)
    finally:
        dme.stop()
