#!/usr/bin/env node
// Static route audit — diffs internal navigation against the route tree.
//
// Walks `src/app/` to enumerate every Next.js page route, then scans
// every `.tsx` / `.ts` under `src/` for literal-string internal links
// (`href="/..."`, `<Link href="/...">`, `router.push("/...")`,
// `router.replace("/...")`, `router.prefetch("/...")`) and reports any
// that don't resolve to a known route.
//
// Skipped (intentional):
//   * External URLs (https://, http://, mailto:, tel:, ftp:)
//   * Anchor / fragment / blank (`#…`, ``, `javascript:`)
//   * Relative paths (don't start with `/`)
//   * Dynamic href values (template literals, variables) — we only
//     verify literal strings; template `/wallets/${id}` is trusted
//   * API paths (`/api/...`, `/v1/...`, `/platform/...`) — those are
//     backend endpoints, not Next.js routes
//
// Exit code 0 when all internal links resolve; 1 when orphans found.
//
// Run: `npm run audit:ux`
//
// Why .mjs and not .ts: this is a maintenance script that runs in CI
// and locally before push. Avoiding a TS-compile step keeps it simple
// (no tsx loader, no transpile) and the script itself is dep-free.

import { readdir, readFile, stat } from "node:fs/promises";
import { join, relative, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const APP_DIR = resolve(ROOT, "src/app");
const SRC_DIR = resolve(ROOT, "src");

// ───────────────────────── route enumeration ─────────────────────────

/** Convert a `page.tsx` filesystem path to a Next.js route + regex.
 *  Examples:
 *    src/app/wallets/page.tsx                  → /wallets
 *    src/app/(authenticated)/wallets/page.tsx  → /wallets        (groups stripped)
 *    src/app/wallets/[name]/page.tsx           → /wallets/[name] (param slot)
 *    src/app/wallets/[name]/send/page.tsx      → /wallets/[name]/send
 */
function routeFromPath(p) {
  const rel = relative(APP_DIR, p);
  // strip trailing /page.tsx
  let segs = rel.split("/").slice(0, -1);
  // drop route groups `(group)` — they don't show up in the URL
  segs = segs.filter((s) => !(s.startsWith("(") && s.endsWith(")")));
  return "/" + segs.join("/");
}

/** Convert a route with [param] slots into a regex matching concrete
 *  hrefs. `[name]` matches one non-slash segment.
 */
function routeToRegex(route) {
  const safe = route
    .split("/")
    .map((s) => {
      if (s.startsWith("[") && s.endsWith("]")) return "[^/]+";
      return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    })
    .join("/");
  return new RegExp(`^${safe}$`);
}

async function walk(dir) {
  const out = [];
  for (const name of await readdir(dir)) {
    if (name === "node_modules" || name === ".next") continue;
    const full = join(dir, name);
    const st = await stat(full);
    if (st.isDirectory()) {
      out.push(...(await walk(full)));
    } else {
      out.push(full);
    }
  }
  return out;
}

async function enumerateRoutes() {
  const all = await walk(APP_DIR);
  const pages = all.filter((p) => p.endsWith("/page.tsx") || p.endsWith("/page.ts"));
  const routes = pages.map(routeFromPath);
  // Always include `/` since the public landing lives at `src/app/page.tsx`
  // which routeFromPath produces; nothing extra needed.
  return Array.from(new Set(routes)).sort();
}

// ───────────────────────── link extraction ─────────────────────────

// Patterns picked from real Orgon code (verified):
//   href="/path"                 (anchors, <Link>, framer-motion)
//   href={"/path"}               (jsx expression with literal)
//   router.push("/path")         (next/navigation)
//   router.replace("/path")
//   router.prefetch("/path")
//   redirect("/path")            (server actions / RSC)
// Template literals (`href={`/foo/${id}`}`) and variable hrefs
// (`href={someVar}`) are deliberately skipped — only literals.
const LINK_PATTERNS = [
  /href\s*=\s*["']([^"']+)["']/g,
  /href\s*=\s*\{\s*["']([^"']+)["']\s*\}/g,
  /router\.(push|replace|prefetch)\s*\(\s*["']([^"']+)["']/g,
  /\bredirect\s*\(\s*["']([^"']+)["']/g,
];

function shouldSkip(url) {
  if (!url) return true;
  if (url.startsWith("http://") || url.startsWith("https://")) return true;
  if (url.startsWith("mailto:") || url.startsWith("tel:") || url.startsWith("ftp:")) return true;
  if (url.startsWith("javascript:") || url.startsWith("#") || url === "") return true;
  if (!url.startsWith("/")) return true;
  // Backend API endpoints — not Next.js routes
  if (url.startsWith("/api/")) return true;
  if (url.startsWith("/v1/")) return true;
  if (url.startsWith("/platform/")) return true;
  // OpenAPI / docs served by FastAPI, not Next
  if (url === "/api/docs" || url === "/api/redoc" || url === "/api/openapi.json") return true;
  return false;
}

function stripQueryAndHash(url) {
  return url.split("?")[0].split("#")[0];
}

async function extractLinks(file) {
  const src = await readFile(file, "utf8");
  const found = new Set();
  for (const pat of LINK_PATTERNS) {
    pat.lastIndex = 0;
    let m;
    while ((m = pat.exec(src)) !== null) {
      // For router.push/replace/prefetch the URL is in capture group 2,
      // for href patterns it's in group 1. The last capture group is
      // always the URL.
      const url = m[m.length - 1];
      if (shouldSkip(url)) continue;
      found.add(stripQueryAndHash(url));
    }
  }
  return Array.from(found);
}

// ───────────────────────── main ─────────────────────────

async function main() {
  const routes = await enumerateRoutes();
  const routeRegexes = routes.map(routeToRegex);

  const allFiles = (await walk(SRC_DIR)).filter(
    (f) => f.endsWith(".tsx") || f.endsWith(".ts"),
  );

  // url → list of files that mention it
  const linkToFiles = new Map();
  for (const f of allFiles) {
    const links = await extractLinks(f);
    for (const l of links) {
      if (!linkToFiles.has(l)) linkToFiles.set(l, []);
      linkToFiles.get(l).push(relative(ROOT, f));
    }
  }

  const orphans = [];
  for (const [url, files] of linkToFiles.entries()) {
    const ok = routeRegexes.some((re) => re.test(url));
    if (!ok) orphans.push({ url, files });
  }

  // Sorted, predictable output
  orphans.sort((a, b) => a.url.localeCompare(b.url));

  console.log(`audit-routes: ${routes.length} routes, ${linkToFiles.size} unique internal links scanned`);
  if (orphans.length === 0) {
    console.log("audit-routes: OK — every internal link resolves to a known route.");
    process.exit(0);
  }

  console.error(`audit-routes: FAIL — ${orphans.length} orphan link(s):`);
  for (const o of orphans) {
    console.error(`  ${o.url}`);
    for (const f of o.files.slice(0, 5)) {
      console.error(`    ← ${f}`);
    }
    if (o.files.length > 5) {
      console.error(`    … ${o.files.length - 5} more`);
    }
  }
  console.error("");
  console.error("Each orphan is either a typo, a route that was removed,");
  console.error("or a /api|/v1|/platform endpoint that should be skipped");
  console.error("(add the prefix to shouldSkip() in this script).");
  process.exit(1);
}

main().catch((e) => {
  console.error("audit-routes: crashed:", e);
  process.exit(2);
});
