import { chromium } from "playwright"
const FRONTEND = process.env.FRONTEND || "http://localhost:5173"
const b = await chromium.launch()
for (const [w, h, pfx] of [[1440, 900, "d"], [390, 844, "m"]]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h } })
  const p = await ctx.newPage()
  for (const route of ["login", "register", "terms"]) {
    await p.goto(`${FRONTEND}/${route}`, { waitUntil: "load" })
    await p.waitForTimeout(900)
    await p.screenshot({ path: `auth-${pfx}-${route}.png` })
    console.log("shot auth-" + pfx + "-" + route)
  }
  await ctx.close()
}
await b.close()
