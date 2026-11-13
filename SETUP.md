# Setup (about 15 minutes, no coding)

## 1. Get free Fuel Finder API credentials
1. Go to https://www.developer.fuel-finder.service.gov.uk/ and follow "Get started" for information recipients.
2. Sign in with a GOV.UK One Login (free; create one if needed).
3. Create an application. You will receive a **Client ID** and a **Client secret**. Keep them private.

## 2. Create a GitHub repository
1. Sign up / sign in at https://github.com.
2. Click **New repository**. Name it e.g. `fuel-tracker`, set it to **Public** (free Pages and Actions need this), and create it.
3. Click **uploading an existing file**, drag in the *contents* of the unzipped folder (including the hidden `.github` folder: on Mac press Cmd+Shift+. to show hidden files; on Windows enable "Hidden items"), and commit.
   Check that `.github/workflows/refresh.yml`, `scripts/refresh.py`, `config.json` and `docs/index.html` all appear in the repo.

## 3. Add your credentials as secrets
Repo > **Settings > Secrets and variables > Actions > New repository secret**. Add two:
- `FF_CLIENT_ID` = your Client ID
- `FF_CLIENT_SECRET` = your Client secret

## 4. Turn on GitHub Pages
Repo > **Settings > Pages > Build and deployment > Source: GitHub Actions**.

## 5. Run it
Repo > **Actions > Refresh fuel prices > Run workflow**. After a few minutes your site is live at
`https://YOUR-USERNAME.github.io/fuel-tracker/`. Bookmark it or add it to your phone's home screen.
It then refreshes itself every 3 hours (change the `cron` line in `.github/workflows/refresh.yml` to alter this).

## 6. Check your four stations matched
Open the finished run, then the "Fetch prices from Fuel Finder" log. Look for lines like
`MATCH Tesco Wokingham -> ... RG40 2NS`. If you see `NO MATCH`, edit `config.json`:
- set `postcode` to the station's exact postcode, or
- change `near` = `[latitude, longitude, radius_km]` to the station's coordinates (right-click the spot in Google Maps to copy them).
The Camberley Meadows entries use approximate coordinates, so check those two first.

## If something goes wrong
- **Credentials error:** re-check both secrets for stray spaces. Repeated bad logins lock the token endpoint for about 5 minutes.
- **Run fails reading the data:** the official API's field names may differ from what the script expects. Run locally with
  `FF_CLIENT_ID=... FF_CLIENT_SECRET=... python scripts/refresh.py --inspect`, then compare the printed sample with the field names in `scripts/refresh.py` (the `pick(...)` calls in `main`). This was written from documentation of the API, not tested against your credentials, so a small tweak may be needed on first run.
- **Prices stop updating after ~2 months:** GitHub pauses scheduled runs on repos with no activity for 60 days. Open the Actions tab and click Enable, or make any small commit.
- **Map says "No data yet":** the first workflow run must finish green first.

## Notes
- Data licence: Open Government Licence v3.0. If you share the site publicly, keep the attribution and read the Fuel Finder Fair Use Policy.
- Map tiles are OpenStreetMap's free tiles, fine for personal use.
