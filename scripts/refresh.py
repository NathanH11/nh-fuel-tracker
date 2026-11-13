#!/usr/bin/env python3
"""Fetch every UK forecourt + prices from the official GOV.UK Fuel Finder API
and write docs/data/stations.json for the website.

Usage:
  FF_CLIENT_ID=... FF_CLIENT_SECRET=... python scripts/refresh.py
  ... python scripts/refresh.py --inspect   # print raw field names (no secrets)
"""
import os, sys, json, time, math, datetime, urllib.request, urllib.error

BASE = "https://www.fuel-finder.service.gov.uk"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "data", "stations.json")
INSPECT = "--inspect" in sys.argv
FUELS = {"B7_STANDARD": "d", "E10": "p", "B7_PREMIUM": "sd", "E5": "sp"}


def http(method, url, body=None, token=None, tries=4):
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; uk-fuel-tracker/1.0)",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    for n in range(tries):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body_txt = e.read().decode(errors="replace")[:500]
            print(f"HTTP {e.code} from {url}: {body_txt}", flush=True)
            if e.code in (400, 403, 404) and ("batch-number" in url or "oauth" in url):
                raise
            if e.code in (429, 500, 502, 503, 504) and n < tries - 1:
                time.sleep(10 * (n + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if n < tries - 1:
                time.sleep(10 * (n + 1))
                continue
            raise


def pick(d, *keys):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return None


def rows_of(j):
    if isinstance(j, list):
        return j
    if isinstance(j, dict):
        for k in ("data", "results", "items", "stations", "fuel_prices"):
            v = j.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                r = rows_of(v)
                if r:
                    return r
    return []


def get_token():
    cid = os.environ.get("FF_CLIENT_ID", "").strip()
    sec = os.environ.get("FF_CLIENT_SECRET", "").strip()
    if not cid or not sec:
        sys.exit("Set FF_CLIENT_ID and FF_CLIENT_SECRET.")
    print(f"Client ID length: {len(cid)}, secret length: {len(sec)}", flush=True)
    j = http("POST", BASE + "/api/v1/oauth/generate_access_token",
             {"client_id": cid, "client_secret": sec})
    inner = j.get("data", {}) if isinstance(j, dict) else {}
    tok = pick(j, "access_token") or pick(inner, "access_token")
    if not tok:
        sys.exit("No access token in the response. Check your credentials.")
    return tok


def fetch_all(path, token):
    out, batch = [], 1
    while batch <= 60:
        try:
            rows = rows_of(http("GET", f"{BASE}{path}?batch-number={batch}", token=token))
        except urllib.error.HTTPError as e:
            if out and e.code in (400, 404):
                break
            raise
        if not rows:
            break
        out.extend(rows)
        print(f"  {path} batch {batch}: {len(rows)} rows", flush=True)
        batch += 1
    return out


def sid(r):
    return pick(r, "node_id", "pfs_id", "site_id", "id")


def km(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


def norm_price(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if v < 10:
        v *= 100  # pounds -> pence
    return round(v, 1) if 50 <= v <= 400 else None


def main():
    token = get_token()
    print("Fetching
