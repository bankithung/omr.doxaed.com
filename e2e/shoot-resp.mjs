import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = process.env.FRONTEND || "http://localhost:5173"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "amber")
mkdirSync(OUT, { recursive: true })

const b = await chromium.launch()

async function sweep(p) {
  const tot = await p.evaluate(() => document.body.scrollHeight)
  for (let y = 0; y <= tot; y += 300) { await p.evaluate((yy) => scrollTo(0, yy), y); await p.waitForTimeout(50) }
  await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(300)
}
async function shotSection(p, text, file, nudge = -40) {
  try {
    const t = p.getByText(text, { exact: false }).first()
    await t.scrollIntoViewIfNeeded(); await p.waitForTimeout(500)
    await p.evaluate((n) => window.scrollBy(0, n), nudge); await p.waitForTimeout(500)
    await p.screenshot({ path: `${OUT}/${file}` })
    console.log(file)
  } catch (e) { console.log("MISS", text, String(e).slice(0, 50)) }
}

for (const w of [390, 700, 1440]) {
  const ctx = await b.newContext({ viewport: { width: w, height: 900 } })
  const p = await ctx.newPage()
  await p.goto(`${F}/`, { waitUntil: "load" }); await p.waitForTimeout(1200); await sweep(p)
  await shotSection(p, "Per-student shuffle", `7-bento-${w}.png`)
  await shotSection(p, "Generate shuffled sheets", `7-howit-${w}.png`)
  await ctx.close()
}
await b.close()
console.log("DONE")
