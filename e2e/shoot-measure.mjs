import { chromium } from "playwright"
const F = process.env.FRONTEND || "http://localhost:5173"
const b = await chromium.launch()
const p = await (await b.newContext({ viewport: { width: 1440, height: 1000 } })).newPage()
await p.goto(`${F}/`, { waitUntil: "load" })
await p.waitForTimeout(1500)
const tot = await p.evaluate(() => document.body.scrollHeight)
for (let y = 0; y <= tot; y += 320) { await p.evaluate((yy) => scrollTo(0, yy), y); await p.waitForTimeout(50) }
await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(300)
const chain = await p.evaluate(() => {
  // start at the DealOut flex container: the bank text → up to the flex row
  const bank = [...document.querySelectorAll("p")].find((e) => e.textContent.trim() === "One question bank")
  if (!bank) return { err: "no bank text" }
  let el = bank
  const out = []
  for (let i = 0; i < 8 && el; i++) {
    const r = el.getBoundingClientRect()
    const cs = getComputedStyle(el)
    out.push({
      tag: el.tagName.toLowerCase(),
      w: Math.round(r.width),
      display: cs.display,
      cls: (el.className || "").toString().slice(0, 70),
    })
    el = el.parentElement
  }
  return { out }
})
console.log(JSON.stringify(chain, null, 2))
await b.close()
