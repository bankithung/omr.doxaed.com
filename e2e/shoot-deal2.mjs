import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = process.env.FRONTEND || "http://localhost:5173"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "amber")
mkdirSync(OUT, { recursive: true })

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 } })
const p = await ctx.newPage()
await p.goto(`${F}/`, { waitUntil: "load" })
await p.waitForTimeout(1500)

// Sweep the whole page so every in-view animation arms, then return.
const tot = await p.evaluate(() => document.body.scrollHeight)
for (let y = 0; y <= tot; y += 320) { await p.evaluate((yy) => scrollTo(0, yy), y); await p.waitForTimeout(80) }
await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(600)

// 1) DashboardPreview — the .shadow-xl window (denser 14-row answer sheet)
try {
  const dash = p.locator(".shadow-xl").first()
  await dash.scrollIntoViewIfNeeded(); await p.waitForTimeout(700)
  await dash.screenshot({ path: `${OUT}/10-dashboard-preview.png` })
  console.log("dashboard")
} catch (e) { console.log("MISS dash", String(e).slice(0, 90)) }

// 2) DealOut — the card holding "Class X · 40 students" (animated connectors)
try {
  const t = p.getByText("Class X", { exact: false }).first()
  await t.scrollIntoViewIfNeeded(); await p.waitForTimeout(500)
  const card = t.locator("xpath=ancestor::div[contains(@class,'bg-card')][1]")
  await card.screenshot({ path: `${OUT}/11-dealout-connectors.png` })
  console.log("dealout")
} catch (e) { console.log("MISS deal", String(e).slice(0, 90)) }

await ctx.close(); await b.close()
console.log("DONE")
