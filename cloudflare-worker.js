// Cloudflare Worker with two jobs:
//  1. PROXY: passes requests through to the GOV.UK Fuel Finder API. The API refused requests coming
//     straight from GitHub's servers (HTTP 403), and routing them through here got round that.
//  2. TIMER: every time its Cron Trigger fires, it tells GitHub to run the "Refresh fuel prices" workflow.
//     (GitHub's own scheduler is unreliable: it often runs only a few times a day.)
//
// Setup: add a secret called GITHUB_TOKEN (a fine-grained token with Actions read/write on this one repo)
// and add a Cron Trigger such as */30 * * * *. See SETUP.md.

const GH_REPO = "NathanH11/nh-fuel-tracker";   // your GitHub username/repository
const GH_WORKFLOW = "refresh.yml";             // the workflow file to run
const GH_REF = "main";                         // the branch

export default {
  // 1. The proxy
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
  },

  // 2. The timer
  async scheduled(event, env, ctx) {
    ctx.waitUntil(triggerRefresh(env));
  },
};

async function triggerRefresh(env) {
  if (!env.GITHUB_TOKEN) {
    console.log("GITHUB_TOKEN secret is missing, so the refresh was not started.");
    return;
  }
  const res = await fetch(
    `https://api.github.com/repos/${GH_REPO}/actions/workflows/${GH_WORKFLOW}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "nh-fuel-tracker-timer",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: GH_REF }),
    }
  );
  if (res.status === 204) {
    console.log("Refresh started on GitHub.");
  } else {
    console.log("GitHub refused the request:", res.status, await res.text());
  }
}
