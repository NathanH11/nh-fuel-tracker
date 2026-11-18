// Cloudflare Worker with two jobs:
//  1. AUTHENTICATED PROXY: only the refresh workflow, which knows PROXY_SECRET,
//     can use the three Fuel Finder API operations required by scripts/refresh.py.
//  2. TIMER: Cron Trigger starts the GitHub Actions refresh workflow.
//
// Required Worker secrets:
//   PROXY_SECRET  - a long random value shared with GitHub Actions as FF_PROXY_SECRET
//   GITHUB_TOKEN  - fine-grained token with Actions read/write on this repository only

const GH_REPO = "NathanH11/nh-fuel-tracker";
const GH_WORKFLOW = "refresh.yml";
const GH_REF = "main";
const UPSTREAM = "https://www.fuel-finder.service.gov.uk";
const MAX_BODY_BYTES = 16 * 1024;

const ALLOWED_GET_PATHS = new Set([
  "/api/v1/pfs",
  "/api/v1/pfs/fuel-prices",
]);
const TOKEN_PATH = "/api/v1/oauth/generate_access_token";

function jsonError(status, message) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

function validBatchQuery(url) {
  const entries = [...url.searchParams.entries()];
  if (entries.length !== 1 || entries[0][0] !== "batch-number") return false;
  const value = entries[0][1];
  return /^[1-9][0-9]?$/.test(value) && Number(value) <= 60;
}

export default {
  async fetch(request, env) {
    // This endpoint is intended for the server-side GitHub refresh job, not browsers.
    if (request.method !== "GET" && request.method !== "POST") {
      return jsonError(405, "Method not allowed");
    }

    if (!env.PROXY_SECRET) {
      console.error("PROXY_SECRET Worker secret is not configured");
      return jsonError(503, "Proxy is not configured");
    }

    const suppliedSecret = request.headers.get("X-Proxy-Auth") || "";
    if (suppliedSecret.length !== env.PROXY_SECRET.length || suppliedSecret !== env.PROXY_SECRET) {
      return jsonError(401, "Unauthorised");
    }

    const incoming = new URL(request.url);
    let upstreamPath;

    if (request.method === "POST" && incoming.pathname === TOKEN_PATH && incoming.search === "") {
      const contentType = request.headers.get("Content-Type") || "";
      if (!contentType.toLowerCase().startsWith("application/json")) {
        return jsonError(415, "JSON required");
      }
      const declaredLength = Number(request.headers.get("Content-Length") || 0);
      if (declaredLength > MAX_BODY_BYTES) return jsonError(413, "Request too large");
      upstreamPath = TOKEN_PATH;
    } else if (request.method === "GET" && ALLOWED_GET_PATHS.has(incoming.pathname) && validBatchQuery(incoming)) {
      // Data endpoints must carry the Fuel Finder access token too.
      const bearer = request.headers.get("Authorization") || "";
      if (!bearer.startsWith("Bearer ") || bearer.length <= 7) {
        return jsonError(401, "Fuel Finder bearer token required");
      }
      upstreamPath = incoming.pathname + "?batch-number=" + incoming.searchParams.get("batch-number");
    } else {
      return jsonError(403, "Endpoint not permitted");
    }

    const headers = new Headers({
      "Accept": "application/json",
      "User-Agent": "Mozilla/5.0 (compatible; uk-fuel-tracker/1.0)",
    });
    // Forward only the headers needed by Fuel Finder. Never forward the proxy secret.
    const authorization = request.headers.get("Authorization");
    if (authorization) headers.set("Authorization", authorization);
    if (request.method === "POST") headers.set("Content-Type", "application/json");

    let body;
    if (request.method === "POST") {
      body = await request.arrayBuffer();
      if (body.byteLength > MAX_BODY_BYTES) return jsonError(413, "Request too large");
    }

    try {
      const upstream = await fetch(UPSTREAM + upstreamPath, {
        method: request.method,
        headers,
        body,
        redirect: "manual",
      });
      // Do not relay redirects to arbitrary destinations.
      if (upstream.status >= 300 && upstream.status < 400) {
        return jsonError(502, "Unexpected upstream redirect");
      }
      const responseHeaders = new Headers(upstream.headers);
      responseHeaders.set("Cache-Control", "no-store");
      responseHeaders.set("X-Content-Type-Options", "nosniff");
      responseHeaders.delete("Set-Cookie");
      return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
    } catch (error) {
      console.error("Fuel Finder upstream request failed", error);
      return jsonError(502, "Fuel Finder request failed");
    }
  },

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
