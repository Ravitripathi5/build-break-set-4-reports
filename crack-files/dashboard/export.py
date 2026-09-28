"""Tiny API: GET /revenue?store=north returns revenue rows for one store."""
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

DB = sqlite3.connect("reports.db", check_same_thread=False)
DB.execute("CREATE TABLE IF NOT EXISTS revenue (day TEXT, store TEXT, amount REAL)")


def revenue_for(store):
    query = f"SELECT day, amount FROM revenue WHERE store = '{store}'"
    return DB.execute(query).fetchall()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        store = parse_qs(urlparse(self.path).query).get("store", [""])[0]
        body = json.dumps(revenue_for(store)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
