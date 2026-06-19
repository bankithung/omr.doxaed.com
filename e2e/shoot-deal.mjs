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

await p.goto(`${F}/`, { waitUntil: "load" })
await p.waitForTimeout(2200) // let hero settle

async function shotAt(text, file, nudge = -90) {
  try {
    const el = p.getByText(text, { exact: false }).first()
    await el.scrollIntoViewIfNeeded()
    await p.waitForTimeout(300)
    await p.evaluate((n) => window.scrollBy(0, n), nudge)
    await p.waitForTimeout(900) // let in-view animations arm
    await p.screenshot({ path: `${OUT}/${file}` })
    console.log(file)
  } catch (e) {
    console.log("MISS", text, String(e).slice(0, 80))
  }
}

// DashboardPreview (hero app screenshot) — the denser 14-row answer sheet
await shotAt("omr.doxaed.com/tests/midterm-physics", "10-dashboard-preview.png", -120)
// DealOut "Generate shuffled sheets" — the new animated connectors
await shotAt("One question bank", "11-dealout-connectors.png", -160)

await ctx.close(); await b.close()
console.log("DONE")
