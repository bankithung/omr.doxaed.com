import { chromium } from "playwright"

const FRONTEND = process.env.FRONTEND || "http://localhost:5173"
const browser = await chromium.launch()
const VW = Number(process.env.VW || 1440)
const VH = Number(process.env.VH || 900)
const ctx = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: 1 })
const page = await ctx.newPage()
await page.goto(`${FRONTEND}/`, { waitUntil: "load" })
await page.waitForTimeout(900) // hero entrance

const PFX = process.env.PFX || "cine"
const shot = async (label) => {
  await page.screenshot({ path: `${PFX}-${label}.png` }) // viewport-only
  console.log("shot " + PFX + "-" + label)
}

// Hero (top)
await page.evaluate(() => window.scrollTo(0, 0))
await page.waitForTimeout(700)
await shot("0-hero")

// Find the pinned centerpiece section
const cp = await page.evaluate(() => {
  let el = document.querySelector("[data-scrolljack]")
  if (!el) {
    // fallback: the tallest <section>
    const secs = [...document.querySelectorAll("section")]
    el = secs.sort((a, b) => b.offsetHeight - a.offsetHeight)[0]
  }
  return el ? { top: el.offsetTop, height: el.offsetHeight } : null
})
console.log("centerpiece:", JSON.stringify(cp))

if (cp) {
  const vh = VH
  const range = cp.height - vh
  // 4 acts: assemble / fan-out / scan / analytics
  const acts = [
    [0.13, "1-assemble"],
    [0.4, "2-fanout"],
    [0.66, "3-scan"],
    [0.92, "4-analytics"],
  ]
  for (const [prog, name] of acts) {
    const y = Math.round(cp.top + prog * range)
    await page.evaluate((yy) => window.scrollTo(0, yy), y)
    await page.waitForTimeout(1100) // let the spring settle
    await shot(name)
  }
}

// Below the centerpiece: bento, then near the bottom (CTA)
const total = await page.evaluate(() => document.body.scrollHeight)
await page.evaluate((t) => window.scrollTo(0, t * 0.86), total)
await page.waitForTimeout(900)
await shot("5-bento-marquee")
await page.evaluate((t) => window.scrollTo(0, t), total)
await page.waitForTimeout(900)
await shot("6-cta-footer")

await ctx.close()
await browser.close()
console.log("done")
