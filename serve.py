#!/usr/bin/env python3
"""
Tiny static server for The Hundred — a collection of 100 standalone HTML designs.

Usage:
    python3 serve.py                 # http://localhost:8000
    python3 serve.py 9000            # http://localhost:9000
    python3 serve.py 8000 --bind 0.0.0.0   # also reachable from your phone on the LAN
    python3 serve.py 8000 --open     # launch the browser automatically

Why a server at all: every design in this folder is a self-contained page and
opens fine straight from disk. A server is here because the gallery mounts a
live <iframe> of every design as its thumbnail, and some browsers treat
file:// documents as cross-origin and refuse to frame them. Served over HTTP
the live previews work.

Only stdlib. No dependencies.
"""

import argparse
import functools
import http.server
import os
import socket
import socketserver
import sys
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = "index.html"


class Handler(http.server.SimpleHTTPRequestHandler):
    """Static handler with directory index, no-cache, and correct HTML MIME."""

    def end_headers(self):
        # Designs ship as raw files with no cache-busting, so never let a
        # browser hold on to a stale copy while you iterate.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def guess_type(self, path):
        if path.endswith((".html", ".htm")):
            return "text/html; charset=utf-8"
        if path.endswith(".css"):
            return "text/css; charset=utf-8"
        if path.endswith(".js"):
            return "text/javascript; charset=utf-8"
        if path.endswith(".svg"):
            return "image/svg+xml"
        if path.endswith(".json"):
            return "application/json; charset=utf-8"
        return super().guess_type(path)

    def list_directory(self, path):
        # No directory listings. The gallery is the front door.
        if os.path.isfile(os.path.join(path, INDEX)):
            self.send_response(302)
            self.send_header("Location", INDEX if path.endswith("/") else INDEX)
            self.end_headers()
            return None
        return super().list_directory(path)

    def log_message(self, fmt, *args):
        # Quieter, colourised-ish log that skips the noisy 200s for iframes.
        status = str(args[1]) if len(args) > 1 else ""
        if status.startswith("2") and "GET" in str(args[0]):
            sys.stdout.write(".")
        else:
            sys.stdout.write("\n  %s\n" % (fmt % args))
        sys.stdout.flush()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def lan_ip() -> str:
    """Best-effort LAN address, for reaching the gallery from a phone."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Serve the design gallery over HTTP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("port", nargs="?", type=int, default=8000, help="port (default 8000)")
    ap.add_argument("--bind", default="127.0.0.1", help="interface to bind (default 127.0.0.1)")
    ap.add_argument("--open", action="store_true", help="open the gallery in a browser")
    args = ap.parse_args()

    if not os.path.isfile(os.path.join(ROOT, INDEX)):
        print("error: %s not found in %s" % (INDEX, ROOT), file=sys.stderr)
        return 1

    count = len([f for f in os.listdir(ROOT) if f.endswith(".html")]) - 1

    handler = functools.partial(Handler, directory=ROOT)
    try:
        httpd = Server((args.bind, args.port), handler)
    except OSError as e:
        print("error: cannot bind %s:%d — %s" % (args.bind, args.port, e), file=sys.stderr)
        print("       try a different port, e.g.  python3 serve.py %d" % (args.port + 1), file=sys.stderr)
        return 1

    shown = "127.0.0.1" if args.bind in ("127.0.0.1", "localhost") else args.bind
    url = "http://%s:%d/" % (shown, args.port)

    print("\n  \033[1mThe Hundred\033[0m — %d designs served from %s\n" % (max(count, 0), ROOT))
    print("    %s" % url)
    if args.bind == "0.0.0.0":
        print("    http://%s:%d/   (LAN)" % (lan_ip(), args.port))
    print("\n  Ctrl-C to stop.\n")

    if args.open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  stopped.\n")
    finally:
        httpd.shutdown()
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
