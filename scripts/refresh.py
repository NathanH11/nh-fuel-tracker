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
    print("Fetching forecourts...")
    forecourts = fetch_all("/api/v1/pfs", token)
    print("Fetching prices...")
    prices = fetch_all("/api/v1/pfs/fuel-prices", token)

    if INSPECT:
        print("\n--- forecourt sample ---\n", json.dumps(forecourts[:1], indent=2)[:1500])
        print("\n--- price sample ---\n", json.dumps(prices[:1], indent=2)[:1500])
        return

    by_id = {}
    for r in forecourts:
        loc = r.get("location") if isinstance(r.get("location"), dict) else r
        la, lo = pick(loc, "latitude", "lat"), pick(loc, "longitude", "lng", "lon")
        try:
            la, lo = float(la), float(lo)
        except (TypeError, ValueError):
            continue
        if not (49 < la < 61 and -9 < lo < 3):
            continue
        by_id[sid(r)] = {
            "i": sid(r),
            "n": pick(r, "trading_name", "name", "site_name") or "Petrol station",
            "b": pick(r, "brand_name", "brand") or "",
            "la": round(la, 5), "lo": round(lo, 5),
            "pc": pick(loc, "postcode") or "",
        }

    for r in prices:
        s = by_id.get(sid(r))
        if not s:
            continue
        items = r.get("fuel_prices") if isinstance(r.get("fuel_prices"), list) else [r]
        for it in items:
            key = FUELS.get(str(pick(it, "fuel_type", "fuel") or "").upper())
            price = norm_price(pick(it, "price", "price_per_litre"))
            if key and price is not None:
                s[key] = price
                ts = pick(it, "price_change_effective_timestamp", "price_last_updated", "updated_at")
                if ts and (not s.get("u") or str(ts) > s["u"]):
                    s["u"] = str(ts)

    stations = [s for s in by_id.values() if any(k in s for k in ("d", "p", "sd", "sp"))]
    print(f"{len(by_id)} forecourts, {len(stations)} with prices")
    if len(stations) < 1000:
        sys.exit("Suspiciously few stations: not overwriting previous data.")

    favs = []
    cfg = json.load(open(os.path.join(ROOT, "config.json")))
    for f in cfg["favourites"]:
        brand = f.get("brand", "").lower()
        pc = f.get("postcode", "").replace(" ", "").upper()
        cands = [s for s in stations if brand in (s["b"] + " " + s["n"]).lower()]
        hit = None
        if pc:
            hit = next((s for s in cands if s["pc"].replace(" ", "").upper() == pc), None)
        if not hit and f.get("near"):
            la, lo, r = f["near"]
            near = sorted(((km(la, lo, s["la"], s["lo"]), s) for s in cands), key=lambda x: x[0])
            if near and near[0][0] <= r:
                hit = near[0][1]
        if hit:
            print(f"  MATCH {f['label']} -> {hit['n']} {hit['pc']}")
            favs.append({"label": f["label"], "id": hit["i"]})
        else:
            print(f"  NO MATCH for {f['label']} - adjust config.json")
            favs.append({"label": f["label"], "id": None})

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                   "favs": favs, "stations": stations}, fh, separators=(",", ":"))
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
