import { chromium } from "playwright"
const FRONTEND = process.env.FRONTEND || "http://localhost:5173"
const EMAIL = "teacher@omrflow.test", PASS = "Teacher@12345"
const b = await chromium.launch()
async function run(theme) {
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } })
  await ctx.addInitScript(([t]) => { try { localStorage.setItem("omrflow_onboarded", "1"); localStorage.setItem("theme", t) } catch {} }, [theme])
  const p = await ctx.newPage()
  await p.goto(`${FRONTEND}/login`, { waitUntil: "load" })
  await p.getByPlaceholder("you@example.com").fill(EMAIL)
  await p.getByPlaceholder("••••••••").fill(PASS)
  await p.getByRole("button", { name: "Sign in" }).click()
  await p.waitForURL("**/dashboard", { timeout: 15000 }).catch(() => {})
  for (const [route, name] of [["/dashboard","dashboard"],["/classes","classes"],["/folders","folders"],["/rosters","rosters"],["/organizations","orgs"],["/profile","profile"]]) {
    await p.goto(`${FRONTEND}${route}`, { waitUntil: "load" }); await p.waitForTimeout(1200)
    await p.screenshot({ path: `sweep-${theme}-${name}.png` }); console.log(`sweep-${theme}-${name}`)
  }
  await ctx.close()
}
await run("light"); await run("dark")
await b.close()
