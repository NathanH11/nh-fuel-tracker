// Cloudflare Worker: a tiny pass-through proxy for the GOV.UK Fuel Finder API.
// The API refused requests coming straight from GitHub's servers (HTTP 403), and sending them
// through this Worker got round that. It only ever forwards to the Fuel Finder host,
// and it strips Cloudflare's own tracking headers before forwarding.
export default {
  async fetch(request) {
    const url = new URL(request.url);
    url.hostname = "www.fuel-finder.service.gov.uk";
    url.protocol = "https:";

    const headers = new Headers(request.headers);
    headers.set("Host", "www.fuel-finder.service.gov.uk");
    for (const key of Array.from(headers.keys())) {
      const k = key.toLowerCase();
      if (k.startsWith("cf-") || k.startsWith("x-forwarded-") || k === "x-real-ip" || k === "true-client-ip") {
        headers.delete(key);
      }
    }

    const init = { method: request.method, headers: headers };
    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = await request.arrayBuffer();
    }
    return fetch(url.toString(), init);
  }
};
