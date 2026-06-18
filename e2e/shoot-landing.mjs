import { chromium } from "playwright"

const FRONTEND = process.env.FRONTEND || "http://127.0.0.1:5173"
const browser = await chromium.launch()

for (const [w, h, name] of [[1280, 900, "desktop"], [390, 844, "mobile"]]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 })
  const page = await ctx.newPage()
  await page.goto(`${FRONTEND}/`, { waitUntil: "networkidle" })
  // Scroll through to trigger whileInView reveals, then return to top.
  const total = await page.evaluate(() => document.body.scrollHeight)
  for (let y = 0; y <= total; y += 350) {
    await page.evaluate((yy) => window.scrollTo(0, yy), y)
    await page.waitForTimeout(160)
  }
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(500)
  await page.screenshot({ path: `landing-${name}.png`, fullPage: true })
  console.log(`shot landing-${name}.png (scrollHeight=${total})`)
  await ctx.close()
}
await browser.close()
