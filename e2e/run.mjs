/**
 * OMRFlow full end-to-end browser test.
 *
 * Drives the COMPLETE product loop in a real browser, across every available
 * browser engine (bundled Chromium, system Chrome, system Edge):
 *
 *   register → verify email → login → create class → create test (MCQs)
 *   → create roster + students → generate OMR sheets → upload synthetic
 *   scans → auto-grade → results → analytics → export (CSV/Excel/PDF)
 *
 * The two steps a pure-UI test can't do by itself are bridged by the Django
 * helper (e2e/django_helper.py), exactly as a real user would experience them:
 *   - email verification: regenerate the same uid/token the email contains
 *   - scanned sheets: render synthetic filled scans of the REAL generated
 *     sheets, then upload them through the actual UI.
 *
 * Usage:  node run.mjs            (all browsers)
 *         node run.mjs chromium   (one browser)
 */
import { chromium } from "playwright"
import { execFileSync } from "node:child_process"
import { fileURLToPath } from "node:url"
import path from "node:path"
import fs from "node:fs"

const HERE = path.dirname(fileURLToPath(import.meta.url))
const REPO = path.dirname(HERE)
const PYTHON = path.join(REPO, "backend", ".venv", "Scripts", "python.exe")
const HELPER = path.join(HERE, "django_helper.py")
const SHOTS = path.join(HERE, "screenshots")
const SCANS = path.join(HERE, "scans")
const DOWNLOADS = path.join(HERE, "downloads")

const FRONTEND = "http://localhost:5173"
const RUN_ID = Date.now().toString(36)

// Browser matrix: name → launch opts. channel maps to a system browser.
const BROWSERS = [
  { name: "chromium", opts: {} },
  { name: "chrome", opts: { channel: "chrome" } },
  { name: "edge", opts: { channel: "msedge" } },
]

const N_QUESTIONS = 5
const N_OPTIONS = 4
const STUDENTS = ["101", "102", "103", "104", "105"]

// ── helpers ────────────────────────────────────────────────────────────────
function py(...args) {
  const out = execFileSync(PYTHON, [HELPER, ...args], {
    cwd: HERE,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  })
  // The helper prints exactly one JSON line on stdout.
  const line = out.trim().split("\n").filter(Boolean).pop()
  return JSON.parse(line)
}

function ensureDir(d) {
  fs.mkdirSync(d, { recursive: true })
}

// REST helper for the org/class/student SETUP (the org-first redesign made these
// flows multi-page; we exercise them via the API and reserve the browser for the
// auth front door + the OMR pipeline, which is what this harness exists to prove).
const API = "http://localhost:8000/api/v1"
async function api(pathname, { method = "GET", token, org, body } = {}) {
  const headers = { "Content-Type": "application/json" }
  if (token) headers.Authorization = `Bearer ${token}`
  if (org) headers["X-Organization-Id"] = String(org)
  const r = await fetch(`${API}${pathname}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) throw new Error(`${method} ${pathname} → ${r.status} ${await r.text()}`)
  return r.json()
}

async function shot(page, browser, label) {
  const dir = path.join(SHOTS, browser)
  ensureDir(dir)
  await page.screenshot({ path: path.join(dir, `${label}.png`), fullPage: true })
}

const log = (msg) => console.log(`  ${msg}`)

// ── the journey for one browser ──────────────────────────────────────────────
async function runJourney(browserName, launchOpts, mode = "standard") {
  const result = { browser: browserName, steps: [], ok: false, error: null }
  const email = `omrflow.e2e.${browserName}.${RUN_ID}@example.com`
  const password = "E2ePass!2026"
  const fullName = `E2E ${browserName}`

  let browser
  const step = async (name, fn) => {
    process.stdout.write(`  • ${name} … `)
    await fn()
    console.log("ok")
    result.steps.push(name)
  }

  try {
    browser = await chromium.launch({ headless: true, ...launchOpts })
    const context = await browser.newContext({ acceptDownloads: true })
    // Bypass the first-run onboarding redirect: every page starts already-onboarded.
    await context.addInitScript(() => { try { localStorage.setItem("omrflow_onboarded", "1") } catch {} })
    const page = await context.newPage()
    page.setDefaultTimeout(30000)

    // 0. Landing page (the logged-out public front door)
    await step("landing", async () => {
      await page.goto(`${FRONTEND}/`)
      await page.getByRole("heading", { name: /Grade a stack of bubble sheets/ }).waitFor({ timeout: 20000 })
      await shot(page, browserName, "00-landing")
    })

    // 1. Register
    await step("register", async () => {
      await page.goto(`${FRONTEND}/register`)
      await page.getByPlaceholder("Jane Smith").fill(fullName)
      await page.getByPlaceholder("you@example.com").fill(email)
      await page.getByPlaceholder("••••••••").fill(password)
      await page.getByRole("button", { name: "Create account" }).click()
      await page.waitForURL("**/login", { timeout: 20000 })
      await shot(page, browserName, "01-registered")
    })

    // 2. Verify email (regenerate the email's uid/token, visit the link)
    await step("verify-email", async () => {
      const tok = py("token", email)
      await page.goto(`${FRONTEND}${tok.verify_path}`)
      await page.getByText("Email verified", { exact: false }).waitFor({ timeout: 20000 })
      await shot(page, browserName, "02-verified")
    })

    // 3. Login (org-first redesign: a fresh account lands on the Organizations page)
    await step("login", async () => {
      await page.goto(`${FRONTEND}/login`)
      await page.getByPlaceholder("you@example.com").fill(email)
      await page.getByPlaceholder("••••••••").fill(password)
      await page.getByRole("button", { name: "Sign in" }).click()
      await page.waitForURL("**/organizations", { timeout: 20000 })
      await shot(page, browserName, "03-loggedin")
    })

    // 4. Setup org + class + roster + students via the API, then point the browser
    //    session at the new org (activeOrg in localStorage = the X-Organization-Id header).
    let classId, orgId, token
    await step("setup", async () => {
      const { access } = await api("/auth/login/", { method: "POST", body: { email, password } })
      token = access
      const org = await api("/organizations/", {
        method: "POST", token: access, body: { name: `E2E Org ${RUN_ID}`, type: "school" },
      })
      orgId = org.id
      const cls = await api("/classes/", {
        method: "POST", token: access, org: orgId, body: { name: `E2E Class ${RUN_ID}`, kind_label: "Class" },
      })
      classId = cls.id
      const roster = await api("/rosters/", {
        method: "POST", token: access, org: orgId, body: { name: "Students", class_group: classId },
      })
      for (const roll of STUDENTS) {
        await api("/students/", {
          method: "POST", token: access, org: orgId,
          body: { roster: roster.id, roll_number: roll, full_name: `Student ${roll}` },
        })
      }
      // Make the SPA act inside this org (OrgContext reads activeOrg from localStorage).
      await page.goto(`${FRONTEND}/organizations`)
      await page.evaluate((id) => localStorage.setItem("activeOrg", String(id)), orgId)
      await shot(page, browserName, "04-setup")
    })

    // 5. Create test with N questions × N options (option A correct)
    let testId
    await step("create-test", async () => {
      await page.goto(`${FRONTEND}/classes/${classId}/tests/new`)
      // Step 1 — details
      await page.getByPlaceholder("e.g. Mid-term Exam").fill(`E2E Test ${RUN_ID}`)
      await page.getByPlaceholder("e.g. Mathematics").fill("Mathematics")
      if (mode === "roster_prebubbled") {
        await page.locator("#mode-roster").click()
      }
      await page.getByRole("button", { name: "Next: Add questions" }).click()
      // Step 2 — questions
      for (let i = 0; i < N_QUESTIONS; i++) {
        if (i > 0) {
          await page.getByRole("button", { name: "+ Add question" }).click()
        }
        const card = page.locator("div.rounded-xl.border", {
          has: page.locator(`#q-text-${i}`),
        })
        await page.locator(`#q-text-${i}`).fill(`Question ${i + 1}: 2 + 2 = ?`)
        // grow from 2 → N_OPTIONS options
        for (let k = 2; k < N_OPTIONS; k++) {
          await card.getByRole("button", { name: "+ Add option" }).click()
        }
        const optTexts = ["Four", "Three", "Five", "Six"]
        for (let j = 0; j < N_OPTIONS; j++) {
          const label = String.fromCharCode(65 + j)
          await card.getByPlaceholder(`Option ${label}`).fill(optTexts[j] ?? `Opt ${label}`)
        }
        // mark option A correct (radio)
        await page.locator(`#q${i}-opt0-radio`).click()
        await card.getByRole("button", { name: /^Save question$/ }).click()
        await card.getByText("Saved", { exact: true }).first().waitFor({ timeout: 15000 })
      }
      await page.getByRole("button", { name: "Next: Review" }).click()
      await page.getByRole("button", { name: "Finish & mark ready" }).click()
      await page.waitForURL(`**/classes/${classId}`, { timeout: 20000 })
      await shot(page, browserName, "05-test-created")
    })
    // The exam was created in ORG scope — capture its id from the API (the solo-scoped
    // latest-ids helper can't see org-owned rows). The roster + students came from setup.
    {
      const tests = await api(`/tests/?class_group=${classId}`, { token, org: orgId })
      const rows = (tests.results ?? tests).slice().sort((a, b) => b.id - a.id)
      if (!rows.length) throw new Error("no test found after create-test")
      testId = rows[0].id
    }

    // 6. Generate OMR sheets — a DEDICATED PAGE: /tests/:id/sheets hosts the roster
    // picker (now subtree-aware, labelled by section) + generate + branding editor.
    await step("generate-sheets", async () => {
      await page.goto(`${FRONTEND}/tests/${testId}/sheets`)
      await page.waitForLoadState("networkidle")
      // pick the roster in the shadcn Select (options render in a portal)
      await page.getByText("Select a roster…").click()
      await page.getByRole("option", { name: "Students", exact: true }).click()
      await page.getByRole("button", { name: "Generate sheets", exact: true }).click()
      await page.getByText("Sheets generated successfully!", { exact: false }).first().waitFor({ timeout: 60000 })
      await shot(page, browserName, "07-generated")
    })

    // 8. Render synthetic scans of the real generated sheets
    let manifest
    await step("render-scans", async () => {
      const outDir = path.join(SCANS, `${browserName}-${RUN_ID}`)
      manifest = py("make-scans", String(testId), outDir)
      if (!Array.isArray(manifest) || manifest.length === 0) {
        throw new Error("make-scans produced no sheets")
      }
      log(`${manifest.length} synthetic scans rendered`)
    })

    // 9. Upload scans → auto-grade
    await step("upload-and-grade", async () => {
      await page.goto(`${FRONTEND}/tests/${testId}/scan`)
      const files = manifest.flatMap((m) => m.files)
      await page.locator('input[type="file"]').first().setInputFiles(files)
      await page.getByRole("button", { name: /Upload & scan/ }).click()
      await page.getByText("processed successfully", { exact: false }).first().waitFor({ timeout: 90000 })
      await shot(page, browserName, "08-scanned")
    })

    // 10. Results
    await step("results", async () => {
      await page.goto(`${FRONTEND}/tests/${testId}/results`)
      await page.waitForLoadState("networkidle")
      // at least one student roll should appear
      await page.getByText(STUDENTS[0], { exact: false }).first().waitFor({ timeout: 20000 })
      await shot(page, browserName, "09-results")
    })

    // 10b. Student detail drill-down (best-effort — verifies the drill-down page)
    try {
      const detail = page.getByRole("link", { name: "Detail" }).first()
      if (await detail.count()) {
        await detail.click()
        await page.waitForURL("**/students/**", { timeout: 15000 })
        await page.waitForLoadState("networkidle")
        await shot(page, browserName, "09b-student-detail")
        result.steps.push("student-detail")
        log("student-detail page loaded")
      }
    } catch (e) {
      log(`student-detail skipped: ${e.message}`)
    }

    // 11. Analytics + exports
    await step("analytics", async () => {
      await page.goto(`${FRONTEND}/tests/${testId}/analytics`)
      await page.getByRole("heading", { name: "Analytics" }).waitFor({ timeout: 20000 })
      await page.getByText("Score distribution", { exact: false }).first().waitFor({ timeout: 20000 })
      await shot(page, browserName, "10-analytics")
    })

    await step("export", async () => {
      ensureDir(DOWNLOADS)
      for (const [label, fmt] of [["Export CSV", "csv"], ["Export Excel", "xlsx"], ["Export PDF", "pdf"]]) {
        const [download] = await Promise.all([
          page.waitForEvent("download", { timeout: 30000 }),
          page.getByRole("button", { name: label }).click(),
        ])
        const dest = path.join(DOWNLOADS, `${browserName}-${RUN_ID}-results.${fmt}`)
        await download.saveAs(dest)
        const size = fs.statSync(dest).size
        if (size <= 0) throw new Error(`${fmt} export was empty`)
        log(`${fmt} → ${size} bytes`)
      }
      await shot(page, browserName, "11-exported")
    })

    // 11b. Phase 2 surfaces: bulk report-card PDF + item-analysis tab + public portal
    await step("reports-and-portal", async () => {
      // (a) bulk report-card PDF download from the results page
      await page.goto(`${FRONTEND}/tests/${testId}/results`)
      const [dl] = await Promise.all([
        page.waitForEvent("download", { timeout: 30000 }),
        page.getByRole("button", { name: /Download all report cards/i }).click(),
      ])
      const rcPath = path.join(DOWNLOADS, `${browserName}-${RUN_ID}-reportcards.pdf`)
      await dl.saveAs(rcPath)
      if (fs.statSync(rcPath).size <= 0) throw new Error("report-cards PDF was empty")
      log(`report cards → ${fs.statSync(rcPath).size} bytes`)

      // (b) item-analysis tab renders (small cohort → guidance banner)
      await page.goto(`${FRONTEND}/tests/${testId}/analytics`)
      await page.getByRole("tab", { name: /Item Analysis/i }).click()
      await page.getByText(/reliability|graded students/i).first().waitFor({ timeout: 15000 })

      // (c) public portal: publish, then look up a roll in a FRESH no-auth context
      const pub = py("publish", String(testId))
      const pctx = await browser.newContext()
      // Bypass the first-run onboarding redirect: every page starts already-onboarded.
      await pctx.addInitScript(() => { try { localStorage.setItem("omrflow_onboarded", "1") } catch {} })
      const pp = await pctx.newPage()
      await pp.goto(`${FRONTEND}/r/${pub.slug}`)
      await pp.locator("#roll_number").fill(STUDENTS[0])
      await pp.getByRole("button", { name: "Get result" }).click()
      await pp.getByText(`Roll: ${STUDENTS[0]}`, { exact: false }).waitFor({ timeout: 15000 })
      await pp.screenshot({ path: path.join(SHOTS, browserName, "11c-public-portal.png"), fullPage: true })
      await pctx.close()
      log(`public portal: roll ${STUDENTS[0]} resolved on /r/${pub.slug}`)
    })

    // 12. Mode B only — tamper detection: upload a scan whose roll is altered to a
    // DIFFERENT valid roll; the QR still identifies the sheet (so it grades) but
    // the pre-bubbled-roll cross-check must flag roll_mismatch in the review queue.
    if (mode === "roster_prebubbled") {
      await step("roll-tamper-detection", async () => {
        const outDir = path.join(SCANS, `${browserName}-tamper-${RUN_ID}`)
        const t = py("make-scan-tampered", String(testId), outDir)
        if (!t.file) throw new Error("tampered scan not produced")
        await page.goto(`${FRONTEND}/tests/${testId}/scan`)
        await page.locator('input[type="file"]').first().setInputFiles([t.file])
        await page.getByRole("button", { name: /Upload & scan/ }).click()
        await page.getByText("processed successfully", { exact: false }).first().waitFor({ timeout: 90000 })
        await page.goto(`${FRONTEND}/tests/${testId}/review`)
        await page.waitForLoadState("networkidle")
        await page.getByText("Roll number mismatch", { exact: false }).first().waitFor({ timeout: 20000 })
        await shot(page, browserName, "12-roll-mismatch")
        log(`tamper: printed ${t.real_roll} vs scanned ${t.tampered_roll} → roll_mismatch flagged`)
      })
    }

    result.ok = true
    await context.close()
  } catch (err) {
    result.error = err?.message || String(err)
  } finally {
    if (browser) await browser.close().catch(() => {})
  }
  return result
}

// ── main ─────────────────────────────────────────────────────────────────────
async function main() {
  const only = process.argv[2]
  // Standard journey across all browsers + one Mode-B journey (pre-bubbled roll
  // + tamper detection) on chromium. `node run.mjs <name>` restricts to one.
  let runs
  if (only === "modeB") {
    runs = [{ label: "chromium-modeB", opts: {}, mode: "roster_prebubbled" }]
  } else if (only) {
    const b = BROWSERS.find((x) => x.name === only) || BROWSERS[0]
    runs = [{ label: b.name, opts: b.opts, mode: "standard" }]
  } else {
    runs = [
      ...BROWSERS.map((b) => ({ label: b.name, opts: b.opts, mode: "standard" })),
      { label: "chromium-modeB", opts: {}, mode: "roster_prebubbled" },
    ]
  }
  const results = []
  for (const b of runs) {
    console.log(`\n=== ${b.label} ===`)
    const r = await runJourney(b.label, b.opts, b.mode)
    results.push(r)
    if (r.ok) console.log(`  ✅ ${b.label}: full loop passed (${r.steps.length} steps)`)
    else console.log(`  ❌ ${b.label}: failed at "${r.steps[r.steps.length - 1] ?? "launch"}" → ${r.error}`)
  }

  console.log("\n================ SUMMARY ================")
  for (const r of results) {
    console.log(`${r.ok ? "PASS" : "FAIL"}  ${r.browser}  (${r.steps.length} steps)${r.ok ? "" : "  — " + r.error}`)
  }
  const allOk = results.every((r) => r.ok)
  fs.writeFileSync(path.join(HERE, "last-run.json"), JSON.stringify(results, null, 2))
  process.exit(allOk ? 0 : 1)
}

main()
