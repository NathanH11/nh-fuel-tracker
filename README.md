# UK Fuel Tracker

A personal fuel price website and phone app for Wokingham, Winnersh, Earley, Sandhurst and Camberley, with a zoomable map of every petrol station in the UK. It refreshes itself every 30 minutes, costs nothing to run, and each visitor keeps their own list of favourite stations.

**Live site:** https://nathanh11.github.io/nh-fuel-tracker/

## What it does

| Tab / feature | What you get |
|---|---|
| **My stations** | Your saved stations, cheapest first, for the fuel you chose (diesel by default), with brand logos. A **Fill-up slider** at the top (marks at every eighth of a tank) sets how much you are buying, and each station shows what that fill costs, plus its cost per mile (p/mile). Tap one for all fuel prices and directions. |
| **Nearby** | Every station within a radius of your location (15 miles by default), cheapest first, with distance. |
| **UK map** | Every UK forecourt on a zoomable OpenStreetMap. Dots are green, amber or red (cheap, average, expensive). Your stations show as price boxes, with a gold outline on the cheapest of yours. A blue dot shows where you are. |
| **Best value** | Ranks stations by the *real* cost: filling up plus the fuel burned driving there (uses your mpg). **Around me** ranks stations near you; **On a journey** finds the best value along a route you type in, with a map. |
| **Fuel card** | On the My stations tab, tick *I have a WEX Esso fuel card*. Esso stations then show the card price for each fuel everywhere (lists, map colours, Best value), marked 💳. Tap an Esso station to mark it as not accepting the card. |
| **Star button** | Tap any station (map, Nearby or its detail panel) and press ☆ to add it to My stations, or ★ to remove it. |
| **Settings (⚙️)** | Pick which fuel shows first (diesel, petrol E10, super unleaded, super diesel), the Nearby radius, and your car name, tank size and mpg for fill-up and drive costs. |
| **Install as an app** | In Chrome (Android) choose Install app; on iPhone use Safari, Share, Add to Home Screen. |

The site always uses a dark theme, whatever the phone's setting.

## How it works (the big picture)

```
 GOV.UK Fuel Finder API          (official prices for every UK forecourt)
          ^
          |  requests go through...
 Cloudflare Worker               (a small free proxy; see "Why a Cloudflare Worker?")
          ^
          |
 GitHub Actions                  (runs scripts/refresh.py; started by the Cloudflare timer)
          |  writes docs/data/stations.json
          v
 GitHub Pages                    (hosts the website: docs/index.html + the data file)
          |
          v
 Your phone / browser            (loads the page and the data file; no server needed)
```

1. **The data source.** The UK government's *Fuel Finder* scheme requires fuel retailers to publish their pump prices. Approved developers get a free API (a Client ID and Client secret from the GOV.UK developer portal). Fuel types in the feed are `B7_STANDARD` (diesel), `E10` (petrol), `E5` (super unleaded) and `B7_PREMIUM` (super diesel).
2. **The refresh job.** A GitHub Action (`.github/workflows/refresh.yml`) is started every 30 minutes by a timer in your Cloudflare Worker (see *The Cloudflare timer* below). GitHub's own schedule in that file is kept only as a slow backup (every 6 hours), because GitHub's scheduler is unreliable. The job retries up to three times (6 minutes apart) if the API rate-limits it, and runs triggered by uploading files reuse the last downloaded prices instead of calling the API again, so uploads never use up the API's allowance. It starts `scripts/refresh.py`, which logs in to the API, downloads every forecourt and its prices (in batches), tidies them into one compact file, and works out which stations match the default list in `config.json`.
3. **The website.** The same workflow then publishes the `docs` folder to GitHub Pages. The website is plain HTML, CSS and JavaScript with no server. When you open it, your browser downloads `data/stations.json` and does everything (sorting, distances, colours, fill-up costs) on your device.
4. **Secrets stay secret.** Your API credentials live in GitHub's encrypted *Secrets* and are only used by the refresh job. They are never in the website.

### Why a Cloudflare Worker?

The first runs from GitHub failed with `HTTP 403 Forbidden` at the login step, even though the credentials were right. The API appears to block requests coming from outside the UK, and GitHub's free runners are in the US. Sending the requests via a free Cloudflare Worker fixed it. I haven't been able to confirm the exact reason, but it works, and the code is in `cloudflare-worker.js`.

How it's wired up:
- The Worker receives each request from GitHub, removes Cloudflare's tracking headers, and forwards it to `www.fuel-finder.service.gov.uk`.
- The GitHub secret `FF_BASE_URL` holds the Worker's address (`https://something.workers.dev`, including `https://`). `refresh.py` uses that instead of the government address.
- The Worker is a plain pass-through. Anyone who knew its address could send requests through it, but they would still need valid API credentials, which only you have. It's sensible not to share the address.
- Usage is tiny: about 35 requests per refresh, roughly 1,700 a day, well within Cloudflare's free allowance (100,000 requests a day when this was set up).

## Best value tab

Add your car's **mpg** (and tank size) in Settings, then open **Best value**. Both modes have an **Amount to fill** slider, with marks at every eighth of a tank and labels at empty, quarter, half, three quarters and full. It snaps to the marks when you get close, and the cost reflects how much you are actually putting in.

- **Around me:** for every station in your Nearby radius it adds the fill-up cost (litres x price) to the cost of the fuel burned driving there (and back, if ticked). The cheapest *total* comes first, so a station that is a few pence cheaper but miles away drops down.
- **On a journey:** works like a maps search. Type a start (it defaults to "My location") and a destination, and suggestions appear as you type (postcodes, towns and places). Pick one and a pin appears on the map; once both are chosen the route is drawn with its distance and typical time, and the stations near the route are ranked by fill-up plus the detour. Tap a station and use **Route via here** to open Google Maps with that stop added, which gives you live traffic. The max distance off the route is adjustable.
- **Fuel you already have:** tick *Account for the fuel I already have* and set how full the tank is now. The app works out your range (tank size x mpg x how full it is) and keeps a 15-mile reserve. Around me then only shows stations you can actually reach. On a journey it tells you roughly where along the route you will need to fill up (also marked on the map with a pump pin), shows only the stations you can reach before that, and ranks them by total cost. If you have enough fuel to finish the trip it says so and shows the cheapest top-up options anyway. It assumes you will fill the tank to full from there, so the *Amount to fill* slider is hidden while this is ticked.
- **Cost per mile and range:** every station shows its cost per mile for your car (price per litre x litres per mile from your mpg), and the sliders show how many miles a fill adds and how many miles the fuel in your tank gets you.
- **Estimates:** road distance is guessed as 1.3 times the straight-line distance, miles per gallon are UK gallons, and if no tank size is set it assumes 40 litres. Journey times are typical, not live traffic.
- **Privacy:** only the journey search contacts other services. What you type is sent to postcodes.io (postcodes) and Photon by Komoot (towns and places) to give suggestions and coordinates. The start and end coordinates (the exact position if you use "My location") go to the OSRM demo server to get the route. Nothing is sent to anything of mine, and "Around me" stays entirely on your device.
- **Limits:** these are free public services with fair-use limits, so suggestions or routes can occasionally fail when they are busy. Try again after a minute.

### The Cloudflare timer

GitHub's built-in scheduler is best-effort and often skipped runs (sometimes only a couple a day). So the same Cloudflare Worker also has a **Cron Trigger**, `*/30 * * * *` (every 30 minutes, UTC). Each time it fires, the Worker calls GitHub's API to start the *Refresh fuel prices* workflow, using a fine-grained access token stored as the Worker secret `GITHUB_TOKEN`. That token can only run Actions on this one repository.

- In the Actions list these runs show as *workflow_dispatch* (run by your account).
- If the token expires, the 30-minute runs silently stop and only the 6-hourly backup keeps going. Make a new token and update the secret.

## Fuel card discount (WEX Esso card)

The WEX Esso fuel card takes a set amount off each litre at Esso stations, and the amount depends on the fuel. On the **My stations** tab, tick *I have a WEX Esso fuel card*. The rates start as:

| Esso fuel | In the app | Off per litre |
|---|---|---|
| Synergy Unleaded | Petrol (E10) | 3p |
| Synergy Diesel | Diesel | 4p |
| Supreme+ 99 Unleaded | Super unleaded | 5p |
| Supreme+ Diesel | Super diesel | 6p |

- Every Esso station shows the card price for each fuel, marked 💳, with the pump price alongside in its details.
- The discount counts everywhere: list order, map colours, Nearby, and the cost and ranking on the Best value tab.
- The four rates sit in ⚙️ Settings (under *WEX Esso fuel card discounts*), so you can change them if your card terms change. The tick box itself stays on the My stations tab.
- Some Esso-branded sites (for example those inside other retailers) may not accept the card. Tap a station, then the 💳 button, to mark it as not accepting it (and tap again to put it back).
- Everything is saved on the device, so each person sets up their own card.

## Where things are stored (privacy)

- **Your stations and settings** (favourites, chosen fuel, radius, car name, tank size, mpg, fuel card settings) are saved in your browser's local storage on that device. There are no accounts and nothing is sent to a server, so every person using the site has their own list and can't affect anyone else's. Lists don't sync between devices.
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
| `docs/logos/` *(optional)* | Drop the official logo files here to replace the built-in drawn logos. Name them after the brand, as `.svg` or `.png`: `esso`, `shell`, `bp`, `tesco`, `sainsbury`, `asda`, `costco`, `eg` (also `texaco`, `jet`, `morrisons`, `gulf`, `murco`, `applegreen`). The page uses a file if it finds one. |
| `SETUP.md` | Step-by-step setup from scratch. |

## Everyday tasks

- **Refresh prices now:** Actions, *Refresh fuel prices*, *Run workflow*.
- **Change how often it updates:** in Cloudflare, open your Worker, then Settings, Triggers, Cron Triggers, and edit the expression: `*/30 * * * *` is every 30 minutes, `0 * * * *` is hourly. Going faster isn't worthwhile and the scheme has a Fair Use Policy.
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
| Updates stopped but runs worked before | The GitHub token in the Worker's `GITHUB_TOKEN` secret has probably expired. Create a new one (Actions read/write, this repo only) and update the secret. |
| A station shows `NO MATCH` | Fix its postcode or coordinates in `config.json`. |
| Old icon or old layout on the phone | Close the app fully and reopen. For a new icon, remove the home-screen icon and install again. |
| Station is missing or has no price | It may not be in the official data yet, or hasn't reported that fuel. |

## Limits and licences

- Prices are indicative and may differ at the pump. Always check the price at the pump before filling up.
- Data: UK Government Fuel Finder, used under the Open Government Licence v3.0. Keep the attribution if you share the site, and read the scheme's Fair Use Policy if you make it public.
- Map tiles and data: OpenStreetMap contributors (free tiles are fine for light personal use).
- Free tiers used: GitHub (public repo, Actions, Pages), Cloudflare Workers.
- The API's field names or login method could change in future. If a run starts failing with a data-format error, run the script with `--inspect` to see what changed.
- The built-in brand logos are simple drawings in each brand's colours (Esso, Shell, BP, Sainsbury's, Asda, Costco and EG; Tesco is a plain blue badge with white text); they are my own approximations, not the official artwork, which is trademarked. Use `docs/logos/` to show the real ones.
