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

async function shot(path, file, wait = 900) {
  await p.goto(`${F}${path}`, { waitUntil: "load" })
  await p.waitForTimeout(wait)
  const overlay = await p.locator("vite-error-overlay").count()
  await p.screenshot({ path: `${OUT}/${file}` })
  console.log(file, overlay ? "(VITE ERROR!)" : "")
}

await shot("/security", "30-security.png")
await shot("/faq", "31-faq.png")
await shot("/help", "32-help.png")
await shot("/this-route-does-not-exist", "33-notfound.png")
await shot("/contact", "35-contact.png")

// HowItWorks full-width DealOut (container-query adaptive: should be prominent)
await p.goto(`${F}/`, { waitUntil: "load" })
await p.waitForTimeout(1500)
const tot = await p.evaluate(() => document.body.scrollHeight)
for (let y = 0; y <= tot; y += 320) { await p.evaluate((yy) => scrollTo(0, yy), y); await p.waitForTimeout(70) }
await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(400)
try {
  const t = p.getByText("Generate shuffled sheets", { exact: false }).first()
  await t.scrollIntoViewIfNeeded(); await p.waitForTimeout(600)
  const card = t.locator("xpath=ancestor::div[contains(@class,'rounded-2xl')][1]")
  await card.screenshot({ path: `${OUT}/34-howitworks-dealout.png` })
  console.log("34-howitworks-dealout.png")
} catch (e) { console.log("MISS dealout", String(e).slice(0, 80)) }

await ctx.close(); await b.close()
console.log("DONE")
