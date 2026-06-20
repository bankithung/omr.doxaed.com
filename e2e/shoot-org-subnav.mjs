import { chromium } from "playwright"
import { mkdirSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const F = "http://localhost:5173"
const API = "http://localhost:8000/api/v1"
const OUT = join(dirname(fileURLToPath(import.meta.url)), "screenshots", "org-subnav")
mkdirSync(OUT, { recursive: true })

const { access, refresh } = await (await fetch(`${API}/auth/login/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: "teacher@omrflow.test", password: "Teacher@12345" }) })).json()
const A = { "Content-Type": "application/json", Authorization: `Bearer ${access}` }
const org = await (await fetch(`${API}/organizations/`, { method: "POST", headers: A, body: JSON.stringify({ name: "Grace Academy", type: "school" }) })).json()
console.log("org", org.id, "slug", org.slug)

const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 } })
await ctx.addInitScript(([a, rf, oid]) => { localStorage.setItem("access", a); localStorage.setItem("refresh", rf); localStorage.setItem("activeOrg", oid); localStorage.setItem("omrflow_onboarded", "1") }, [access, refresh, String(org.id)])
const p = await ctx.newPage()
p.on("console", (m) => { if (m.type() === "error") console.log("PAGE ERR:", m.text()) })

// Roles — sub-nav (Roles | Member roles), expect 6 system roles
await p.goto(`${F}/org/${org.slug}/roles`, { waitUntil: "load" })
await p.waitForTimeout(2000)
console.log("overlay:", await p.locator("vite-error-overlay").count())
await p.screenshot({ path: `${OUT}/01-roles.png`, fullPage: true })
// switch to Member roles tab
const memTab = p.getByRole("button", { name: "Member roles" }).first()
if (await memTab.count()) { await memTab.click(); await p.waitForTimeout(600); await p.screenshot({ path: `${OUT}/02-roles-members.png`, fullPage: true }) }

// Settings — sub-nav (General | Sheet branding | Danger zone) + slug field
await p.goto(`${F}/org/${org.slug}/settings`, { waitUntil: "load" })
await p.waitForTimeout(2000)
await p.screenshot({ path: `${OUT}/03-settings-general.png`, fullPage: true })
const brandTab = p.getByRole("button", { name: "Sheet branding" }).first()
if (await brandTab.count()) { await brandTab.click(); await p.waitForTimeout(500); await p.screenshot({ path: `${OUT}/04-settings-branding.png`, fullPage: true }) }

// Members — no branding card anymore
await p.goto(`${F}/org/${org.slug}/members`, { waitUntil: "load" })
await p.waitForTimeout(2000)
await p.screenshot({ path: `${OUT}/05-members.png`, fullPage: true })

await ctx.close(); await b.close()
console.log("DONE")
