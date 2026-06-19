import { chromium } from "playwright"
const F = process.env.FRONTEND || "http://localhost:5173"
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
const p = await ctx.newPage()
// landing hero
await p.goto(`${F}/`, { waitUntil: "load" }); await p.waitForTimeout(1200)
await p.screenshot({ path: "supa-landing-hero.png" }); console.log("hero")
// scroll to trigger reveals, then full page
const tot = await p.evaluate(() => document.body.scrollHeight)
for (let y = 0; y <= tot; y += 400) { await p.evaluate((yy) => scrollTo(0, yy), y); await p.waitForTimeout(120) }
await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(400)
await p.screenshot({ path: "supa-landing-full.png", fullPage: true }); console.log("full")
// login (centered)
await p.goto(`${F}/login`, { waitUntil: "load" }); await p.waitForTimeout(900)
await p.screenshot({ path: "supa-login.png" }); console.log("login")
await ctx.close(); await b.close()
