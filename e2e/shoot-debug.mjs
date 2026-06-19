import { chromium } from "playwright"
const F = process.env.FRONTEND || "http://localhost:5173"
const b = await chromium.launch()
const p = await (await b.newContext({ viewport: { width: 1440, height: 1000 } })).newPage()
await p.goto(`${F}/`, { waitUntil: "load" })
await p.waitForTimeout(1500)
const tot = await p.evaluate(() => document.body.scrollHeight)
for (let y = 0; y <= tot; y += 320) { await p.evaluate((yy) => scrollTo(0, yy), y); await p.waitForTimeout(60) }
await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(400)
const info = await p.evaluate(() => {
  const flow = document.querySelector(".landing-flow")
  if (!flow) return { found: false }
  const svg = flow.closest("svg")
  const wrap = svg?.parentElement
  const r = svg.getBoundingClientRect()
  const wr = wrap.getBoundingClientRect()
  const fcs = getComputedStyle(flow)
  const pathR = flow.getBoundingClientRect()
  return {
    found: true,
    svgRect: { w: Math.round(r.width), h: Math.round(r.height) },
    wrapRect: { w: Math.round(wr.width), h: Math.round(wr.height) },
    wrapDisplay: getComputedStyle(wrap).display,
    svgDisplay: getComputedStyle(svg).display,
    flowStroke: fcs.stroke,
    flowStrokeWidth: fcs.strokeWidth,
    flowDash: fcs.strokeDasharray,
    flowPathRect: { w: Math.round(pathR.width), h: Math.round(pathR.height) },
    pathCount: svg.querySelectorAll("path").length,
    ancestorLandingAnim: !!flow.closest(".landing-anim"),
  }
})
console.log(JSON.stringify(info, null, 2))
await b.close()
