import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = process.env.FRONTEND || "http://localhost:5173"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "amber")
mkdirSync(OUT, { recursive: true })

const b = await chromium.launch()

// Premium auth (desktop)
const dctx = await b.newContext({ viewport: { width: 1440, height: 1000 } })
const dp = await dctx.newPage()
await dp.goto(`${F}/login`, { waitUntil: "load" }); await dp.waitForTimeout(900)
await dp.screenshot({ path: `${OUT}/50-login-premium.png` }); console.log("50-login-premium.png")
await dctx.close()

// Mobile DealOut "Per-student shuffle" — check overflow
for (const w of [360, 390, 414, 768]) {
  const ctx = await b.newContext({ viewport: { width: w, height: 900 } })
  const p = await ctx.newPage()
  await p.goto(`${F}/`, { waitUntil: "load" }); await p.waitForTimeout(1200)
  const tot = await p.evaluate(() => document.body.scrollHeight)
  for (let y = 0; y <= tot; y += 300) { await p.evaluate((yy) => scrollTo(0, yy), y); await p.waitForTimeout(50) }
  await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(300)
  try {
    const t = p.getByText("Per-student shuffle", { exact: false }).first()
    await t.scrollIntoViewIfNeeded(); await p.waitForTimeout(500)
    // climb to the bento tile card
    const card = t.locator("xpath=ancestor::div[contains(@class,'rounded')][2]")
    await card.screenshot({ path: `${OUT}/51-pershuffle-${w}.png` })
    console.log(`51-pershuffle-${w}.png`)
  } catch (e) { console.log("MISS", w, String(e).slice(0, 70)) }
  await ctx.close()
}
await b.close()
console.log("DONE")
