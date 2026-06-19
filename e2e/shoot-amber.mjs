import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = process.env.FRONTEND || "http://localhost:5173"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "amber")
mkdirSync(OUT, { recursive: true })

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
const p = await ctx.newPage()

async function settle(ms = 900) { await p.waitForTimeout(ms) }
async function scrollSweep() {
  const tot = await p.evaluate(() => document.body.scrollHeight)
  for (let y = 0; y <= tot; y += 360) { await p.evaluate((yy) => scrollTo(0, yy), y); await p.waitForTimeout(90) }
  await p.evaluate(() => scrollTo(0, 0)); await settle(400)
}

// 1) Landing hero — amber CTAs + shared header
await p.goto(`${F}/`, { waitUntil: "load" }); await settle(1200)
await p.screenshot({ path: `${OUT}/01-landing-hero.png` }); console.log("landing hero")

// 2) TrustSection — the two-column 20-MCQ answer-sheet card
await scrollSweep()
try {
  const h = p.getByText("Grading you can defend", { exact: false }).first()
  await h.scrollIntoViewIfNeeded(); await settle(700)
  await p.evaluate(() => window.scrollBy(0, -80)); await settle(300)
} catch { /* fall back to mid-page */ }
await p.screenshot({ path: `${OUT}/02-landing-trust.png` }); console.log("trust section")

// 3) Pricing — amber tier cards + header
await p.goto(`${F}/pricing`, { waitUntil: "load" }); await settle(1000)
await p.screenshot({ path: `${OUT}/03-pricing.png` }); console.log("pricing")
await p.screenshot({ path: `${OUT}/03-pricing-full.png`, fullPage: true })

// 4) Login — unified LandingNav header + amber
await p.goto(`${F}/login`, { waitUntil: "load" }); await settle(900)
await p.screenshot({ path: `${OUT}/04-login.png` }); console.log("login")

// 5) Terms — unified header on a legal page
await p.goto(`${F}/terms`, { waitUntil: "load" }); await settle(800)
await p.screenshot({ path: `${OUT}/05-terms.png` }); console.log("terms")

// 6) Features — amber accents on a marketing page
await p.goto(`${F}/features`, { waitUntil: "load" }); await settle(900)
await p.screenshot({ path: `${OUT}/06-features.png` }); console.log("features")

// 7) Mobile login — confirm the shared header + form are responsive
await ctx.close()
const mctx = await b.newContext({ viewport: { width: 390, height: 844 } })
const mp = await mctx.newPage()
await mp.goto(`${F}/login`, { waitUntil: "load" }); await mp.waitForTimeout(800)
await mp.screenshot({ path: `${OUT}/07-login-mobile.png` }); console.log("login mobile")

await mctx.close(); await b.close()
console.log("DONE")
