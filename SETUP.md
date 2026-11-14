# Setup from scratch (about 30 minutes, no coding)

You need: a free GOV.UK One Login, a free GitHub account, and a free Cloudflare account. Read README.md first for how the pieces fit together.

## 1. Get Fuel Finder API credentials
1. Go to https://www.developer.fuel-finder.service.gov.uk/ and register as an information recipient (sign in with GOV.UK One Login).
2. Create an application (name e.g. "My Local Fuel Prices", purpose **Website**, personal non-commercial use).
3. Note the **Client ID** and **Client secret**. Keep them private; the secret may only be shown once.

## 2. Create the GitHub repository
1. At github.com click **New repository**, name it (e.g. `nh-fuel-tracker`), set it to **Public**, and create it.
2. Use **uploading an existing file** on the quick-setup page (or go to `https://github.com/YOUR-USERNAME/YOUR-REPO/upload/main`) and drag in the *contents* of the project folder (not the folder itself): `docs`, `scripts`, `config.json`, `cloudflare-worker.js`, `README.md`, `SETUP.md`.
3. The hidden `.github` folder is often skipped by drag and drop. Check the repo afterwards. If it's missing, click **Add file, Create new file**, type `.github/workflows/refresh.yml` as the name, paste in the workflow text, and commit.

## 3. Create the Cloudflare proxy
1. Sign up at dash.cloudflare.com.
2. **Workers & Pages, Create, Start with Hello World** (do **not** connect a Git repository). Name it e.g. `uk-fuel-proxy`, then **Deploy**.
3. Click **Edit code**, delete the sample, paste the contents of `cloudflare-worker.js`, and **Deploy**.
4. Copy the Worker's address (ends in `.workers.dev`).

## 4. Add the three secrets in GitHub
Repo, **Settings, Secrets and variables, Actions, New repository secret**:
- `FF_CLIENT_ID`: your Client ID
- `FF_CLIENT_SECRET`: your Client secret
- `FF_BASE_URL`: the Worker address, **including `https://`**, with no trailing slash or spaces

## 5. Turn on GitHub Pages
Repo, **Settings, Pages, Build and deployment, Source: GitHub Actions**.

## 6. Run it
**Actions, Refresh fuel prices, Run workflow.** A green tick means your site is live at `https://YOUR-USERNAME.github.io/YOUR-REPO/`. From then on it updates every 30 minutes (the cron line in `refresh.yml` is `17,47 * * * *`).

## 7. Check your stations matched
In the run's *Fetch prices from Fuel Finder* log, look for `MATCH` lines. Fix any `NO MATCH` by editing the postcode or coordinates in `config.json`.

## 8. Put it on your phone
- **Android (Chrome):** open the site, menu (three dots), **Install app**.
- **iPhone (Safari):** Share, **Add to Home Screen**.

For problems, see the Troubleshooting table in README.md.
