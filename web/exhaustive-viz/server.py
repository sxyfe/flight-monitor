#!/usr/bin/env python3
"""穷举结果可视化 — 本地静态服务。"""
import http.server
import os
import socketserver

HOST = os.environ.get("VIZ_HOST", "127.0.0.1")
PORT = int(os.environ.get("VIZ_PORT", "8766"))
DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)


if __name__ == "__main__":
    os.chdir(DIR)
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        print(f"特价雷达: http://{HOST}:{PORT}/")
        httpd.serve_forever()
