# UK Fuel Tracker

A free, self-updating website showing UK fuel prices from the official GOV.UK Fuel Finder scheme.

- **My stations**: diesel first, petrol and other fuels when you tap one (edit `config.json` to change which)
- **UK map**: every forecourt, zoomable, colour-coded by diesel price, with your stations starred

A GitHub Action fetches the official data every 3 hours and republishes the site. Your API secret lives in GitHub Secrets and never reaches the browser.

See SETUP.md for step-by-step instructions.
