# UK Fuel Tracker

A personal fuel price website and phone app for Wokingham, Winnersh, Earley, Sandhurst and Camberley, with a zoomable map of every petrol station in the UK. It refreshes itself every 30 minutes, costs nothing to run, and each visitor keeps their own list of favourite stations.

**Live site:** https://nathanh11.github.io/nh-fuel-tracker/

## What it does

| Tab / feature | What you get |
|---|---|
| **My stations** | Your saved stations, cheapest first, for the fuel you chose (diesel by default), with brand badges and an optional "cost to fill the tank". Tap one for all fuel prices and directions. |
| **Nearby** | Every station within a radius of your location (15 miles by default), cheapest first, with distance. |
| **UK map** | Every UK forecourt on a zoomable OpenStreetMap. Dots are green, amber or red (cheap, average, expensive). Your stations show as price boxes, with a gold outline on the cheapest of yours. A blue dot shows where you are. |
| **Star button** | Tap any station (map, Nearby or its detail panel) and press ☆ to add it to My stations, or ★ to remove it. |
| **Settings (⚙️)** | Pick which fuel shows first (diesel, petrol E10, super unleaded, super diesel), the Nearby radius, and your car name and tank size for fill-up costs. |
| **Install as an app** | In Chrome (Android) choose Install app; on iPhone use Safari, Share, Add to Home Screen. |

## How it works (the big picture)

```
 GOV.UK Fuel Finder API          (official prices for every UK forecourt)
          ^
          |  requests go through...
 Cloudflare Worker               (a small free proxy; see "Why a Cloudflare Worker?")
          ^
          |
 GitHub Actions                  (runs scripts/refresh.py every 30 minutes)
          |  writes docs/data/stations.json
          v
 GitHub Pages                    (hosts the website: docs/index.html + the data file)
          |
          v
 Your phone / browser            (loads the page and the data file; no server needed)
```

1. **The data source.** The UK government's *Fuel Finder* scheme requires fuel retailers to publish their pump prices. Approved developers get a free API (a Client ID and Client secret from the GOV.UK developer portal). Fuel types in the feed are `B7_STANDARD` (diesel), `E10` (petrol), `E5` (super unleaded) and `B7_PREMIUM` (super diesel).
2. **The refresh job.** A GitHub Action (`.github/workflows/refresh.yml`) runs at 17 and 47 minutes past every hour (UTC). It starts `scripts/refresh.py`, which logs in to the API, downloads every forecourt and its prices (in batches), tidies them into one compact file, and works out which stations match the default list in `config.json`.
3. **The website.** The same workflow then publishes the `docs` folder to GitHub Pages. The website is plain HTML, CSS and JavaScript with no server. When you open it, your browser downloads `data/stations.json` and does everything (sorting, distances, colours, fill-up costs) on your device.
4. **Secrets stay secret.** Your API credentials live in GitHub's encrypted *Secrets* and are only used by the refresh job. They are never in the website.

### Why a Cloudflare Worker?

The first runs from GitHub failed with `HTTP 403 Forbidden` at the login step, even though the credentials were right. The API appears to block requests coming from outside the UK, and GitHub's free runners are in the US. Sending the requests via a free Cloudflare Worker fixed it. I haven't been able to confirm the exact reason, but it works, and the code is in `cloudflare-worker.js`.

How it's wired up:
- The Worker receives each request from GitHub, removes Cloudflare's tracking headers, and forwards it to `www.fuel-finder.service.gov.uk`.
- The GitHub secret `FF_BASE_URL` holds the Worker's address (`https://something.workers.dev`, including `https://`). `refresh.py` uses that instead of the government address.
- The Worker is a plain pass-through. Anyone who knew its address could send requests through it, but they would still need valid API credentials, which only you have. It's sensible not to share the address.
- Usage is tiny: about 35 requests per refresh, roughly 1,700 a day, well within Cloudflare's free allowance (100,000 requests a day when this was set up).

## Where things are stored (privacy)

- **Your stations and settings** (favourites, chosen fuel, radius, car name, tank size) are saved in your browser's local storage on that device. There are no accounts and nothing is sent to a server, so every person using the site has their own list and can't affect anyone else's. Lists don't sync between devices.
- **Default list.** If a visitor hasn't changed their stars, they see the default stations from `config.json`. Once they add or remove one, their own list is saved and takes over. *Settings → Reset my stations* returns to the defaults; *Clear my stations* empties the list. To start new visitors with an empty list instead, set `START_WITH_OWNER_LIST` to `false` near the top of the script in `docs/index.html`.
- **Your location** is used only inside your browser, to draw the blue dot and build the Nearby list. It is not stored or sent anywhere. (Map pictures load from OpenStreetMap, which can see roughly which area you view and your IP address, as with any map.)

## What's in this repository

| File | Purpose |
|---|---|
| `.github/workflows/refresh.yml` | The schedule (every 30 minutes) and the build/deploy steps. |
| `scripts/refresh.py` | Downloads and tidies the official data. Run with `--inspect` to see the raw field names. |
| `config.json` | The default stations. Matches use the postcode first, then brand plus distance from approximate coordinates. |
| `cloudflare-worker.js` | The proxy code you pasted into Cloudflare (a copy for reference; the live one is in your Cloudflare account). |
| `docs/index.html` | The whole website. |
| `docs/manifest.webmanifest`, `docs/sw.js`, `docs/icon-*.png` | Make it installable as an app and let it open with the last prices when offline. |
| `docs/logos/` *(optional)* | Drop `tesco.png`, `esso.png`, `shell.png`, `bp.png`, `sainsbury.png` here to replace the coloured badges with real logos. |
| `SETUP.md` | Step-by-step setup from scratch. |

## Everyday tasks

- **Refresh prices now:** Actions, *Refresh fuel prices*, *Run workflow*.
- **Change how often it updates:** edit the `cron` line in `refresh.yml`. `"17,47 * * * *"` is every 30 minutes; `"17 * * * *"` is hourly. Going faster isn't worthwhile and the scheme has a Fair Use Policy.
- **Change the default stations:** edit `config.json`, then check the next run's log (see below). Use the station's exact postcode where you can.
- **Update the site:** upload the new files through GitHub (*Add file*, *Upload files*, or `.../upload/main/docs` for the docs folder). Each change triggers a new build.
- **Check your stations matched:** open the latest run, then *Fetch prices from Fuel Finder*. You should see `MATCH <label> -> <station> <postcode>` for each. `NO MATCH` means the postcode or coordinates in `config.json` need adjusting.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Run fails with `HTTP 403` at `generate_access_token` | The API is refusing the request. Check the `FF_BASE_URL` secret points at your Worker and the Worker is deployed. |
| `unknown url type` / `ValueError` | `FF_BASE_URL` is missing `https://` or has a trailing space. Re-save it. |
| `Set FF_CLIENT_ID and FF_CLIENT_SECRET` | A secret is missing or misnamed. Names are exact and case-sensitive. |
| Python `SyntaxError` after editing `refresh.py` | A line was split when pasting. Re-paste the file as plain text. |
| Site says "No data yet" | The first successful run hasn't finished. Check the Actions tab. |
| "Refreshed" time is old | Scheduled runs pause after 60 days without repo activity: open Actions and click *Enable*, or make any small commit. Also check the latest run is green. |
| A station shows `NO MATCH` | Fix its postcode or coordinates in `config.json`. |
| Old icon or old layout on the phone | Close the app fully and reopen. For a new icon, remove the home-screen icon and install again. |
| Station is missing or has no price | It may not be in the official data yet, or hasn't reported that fuel. |

## Limits and licences

- Prices are indicative and may differ at the pump. Always check the price at the pump before filling up.
- Data: UK Government Fuel Finder, used under the Open Government Licence v3.0. Keep the attribution if you share the site, and read the scheme's Fair Use Policy if you make it public.
- Map tiles and data: OpenStreetMap contributors (free tiles are fine for light personal use).
- Free tiers used: GitHub (public repo, Actions, Pages), Cloudflare Workers.
- The API's field names or login method could change in future. If a run starts failing with a data-format error, run the script with `--inspect` to see what changed.
- The brand badges are simple coloured labels, not the official logos.
