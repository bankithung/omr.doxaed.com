# OMR Engine Spec — OMRFlow

This is the hardest and most differentiating part of the product. Two halves: **generation** (produce reliable, scannable sheets) and **scanning** (read them fast and accurately). The design choices below exist specifically to make scanning fast and trustworthy.

## Core design decisions (read first)

1. **QR code on every sheet/page.** Encodes `sheet_code` **+ page number + total pages** → resolves to the exact `OmrSheet` (test, student, shuffle version, answer key) and which page this is. The scanner never has to *guess* which test/student/version/page a sheet is. This is what makes scanning fast and unambiguous, especially with shuffled questions and multi-page sheets.
2. **Roll number = a bubble grid, not handwriting.** Students bubble their roll number in a digits grid (e.g., columns for each digit, rows 0–9). The scanner detects the filled dots to read the number; no handwriting is read.
3. **Name is pre-printed, not read.** Sheets are personalized per student anyway, so print the name on the sheet. The scanner identifies the student via QR + roll-number dots, then **looks up the name from the database** by that number. **No OCR of any handwriting** — it's the #1 cause of slow, unreliable OMR.
4. **Fiducial (registration) markers** in the corners let us correct rotation, skew, and perspective.
5. **Multi-page sheets auto-stitch.** When a test is long, an `OmrSheet` spans several printed pages. Each page carries its own QR (page i of n) and fiducials. Pages can be scanned in **any order**; the system groups them by `sheet_code` and merges them into one result once all pages are in. A missing page is flagged, not silently graded.
6. **Auto-detect scanning — no manual capture.** The scanner detects a valid sheet in view (by QR + fiducials), auto-grabs it, and moves on — the user does **not** tap a capture button per sheet. It also accepts a multi-page scan/PDF and auto-splits it. (See "Scanning UX" in Part B.)
7. **Low-confidence reads are flagged, never guessed.** Double marks, faint marks, missing QR, unreadable roll, missing page → routed to a manual review queue. Grading integrity over false speed.

## Part A — Sheet generation

### Layout (top to bottom)
- **Header band**: institution/test title, subject, date, pre-printed student name (if known), roll-number label.
- **QR code** (top corner of **every page**): encodes `sheet_code` + page number + total pages. Add a short human-readable code too (fallback if QR damaged).
- **Four corner fiducial markers** on every page: solid filled squares/circles of known size and position used for alignment.
- **Roll-number dot grid**: N digit-columns × 10 rows (0–9), on page 1. Student fills the dots matching their roll number. (Even when name/roll is pre-known, the dots provide a scannable, verifiable identity.)
- **Answer bubble grid**: one row per question, with option bubbles A–F as configured. Group in columns; **overflow to additional pages** when questions don't fit, with question numbering continuing across pages.
- **Quiet margins**: keep clear borders so detection isn't clipped.

### Multi-page sheets
- When a test has more questions than fit on one page, the sheet spans multiple pages. Each page is self-identifying via its QR (`page i of n`) and has its own fiducials, so pages can be scanned in any order and stitched back together. Persist `page_count` and which questions live on which page.

### Personalization & shuffling
- Per sheet, optionally permute question order and/or option order using a stored **seed** (`shuffle_version`).
- Persist for each sheet: `question_order` (ordered Question IDs), optional `option_order`, and the derived `answer_key` (correct option per *printed position*).
- The printed bubble grid follows the sheet's own order. Grading later uses **this sheet's** stored key — not the test default.

### Output
- Render with **ReportLab** for pixel-precise bubble coordinates. Store the exact geometry used (a **template descriptor**: bubble centers, radii, grid origins, fiducial positions in sheet coordinates) alongside the sheet/test. The scanner uses this descriptor to know where to look.
- Batch many students into one print-ready PDF (A4), consistent DPI.
- Recommendation: define **one canonical template per option-count/question-count layout**, versioned, so the scanner maps coordinates deterministically.

### Generation reliability rules
- High-contrast bubbles, consistent size, adequate spacing (avoid bleed between adjacent bubbles).
- Print at a known DPI; embed it. Avoid scaling on print ("actual size").
- Include the human-readable code and a sheet/page index for recovery.

## Part B — Scanning pipeline

Input: an uploaded image (phone photo or scan), single or batch. Runs in a **Celery worker** (async). Steps:

1. **Ingest & normalize** — load image, downscale sensibly, convert to grayscale, denoise. Strip EXIF.
2. **Locate QR** (`pyzbar`) → decode `sheet_code` **+ page number/total** → load the `OmrSheet` + its template descriptor + answer key, and note which page this image is.
   - If no QR: try the human-readable code region / OCR fallback for the short code; if still unknown → `ReviewItem(no_qr)`.
3. **Detect fiducials** → compute the perspective/affine transform to map the image into the template's coordinate space (correct rotation, skew, perspective). If markers not found → `ReviewItem(alignment)`.
4. **Warp** the image to the canonical template space using the transform.
5. **Read roll-number grid** (on the page that carries it — usually page 1) — sample each dot cell, measure fill ratio, pick the filled digit per column. Cross-check against the QR-resolved student; mismatch or unreadable → `ReviewItem(roll_unreadable)` (don't silently override).
6. **Read answer grid** — for each question row on this page, measure fill ratio of each option bubble:
   - One clearly filled → that option.
   - None filled → blank.
   - Two+ filled or ambiguous fill ratios → `flagged` + `ReviewItem(double_mark/faint)`.
7. **Assemble pages** — store this page's reads against its `OmrSheet`. **Grade only once all `total_pages` for that sheet have been scanned** (pages may arrive in any order, across the batch). If pages are still missing, hold the sheet as `partial` and show it as "waiting for page X". A sheet stuck missing a page → `ReviewItem(missing_page)`.
8. **Grade** — map the full set of detected options through the sheet's `question_order`/`answer_key`, apply the test's `MarkingScheme` (correct marks, negative marking, partial, multiple-correct). Compute score, correct/wrong/blank counts.
9. **Persist** — write `StudentResult` + `QuestionResponse`s. Set job/sheet status `done`, or `needs_review` if any flags. Record overall `confidence`.
10. **Report progress** — update `ScanBatch.processed`; client polls (or receives push on) a progress endpoint.

### Bubble detection method
- Work in warped template space where each bubble's center+radius is known from the descriptor.
- For each bubble, compute the **filled-pixel ratio** within its circle (after adaptive thresholding). Classify using high/low thresholds with a hysteresis gap:
  - ratio ≥ `fill_high` → filled
  - ratio ≤ `fill_low` → empty
  - in between → ambiguous → flag.
- Calibrate thresholds against the fixture set (below). Adapt per-sheet using the distribution of all bubbles to handle lighting/darkness variation.

### Performance
- QR + known-geometry sampling is cheap → target **sub-second per sheet** server-side.
- Batches parallelized across workers. Uploads can be compressed client-side first.
- The client's job is **detect + upload only**; heavy processing stays server-side for consistency and easier improvement.

### Scanning UX — auto-detect, no manual capture
The user should never tap "capture" per sheet. Two input modes, both hands-off:

- **Live continuous scan (web camera / mobile):** show the camera feed; lightweight on-device detection watches for a valid sheet (QR present + four fiducials visible + in focus). When detected and stable, the frame is **auto-grabbed** and queued for upload — then the UI immediately readies for the next sheet. The user just places sheets one after another. On-device detection only decides *when to grab*; the actual reading/grading is server-side.
  - Give clear live feedback: "Hold steady", "Got it ✓ (page 2 of 3)", "Move to next sheet". Show a running count of captured sheets and any flagged ones.
- **Bulk file / scanner mode:** accept a multi-page PDF or a folder of images (e.g., from a flatbed/document scanner). The system **auto-splits** it into per-page images and processes them as a batch — no per-sheet interaction.

In both modes, pages are matched and stitched by QR, flagged items go to the review queue, and the user sees live progress. This is what delivers the "just scan, it detects everything" experience.

### Manual review queue (UI)
- Lists flagged sheets with the cropped image region for the issue (e.g., the question row with a double mark).
- Reviewer confirms/corrects the mark; result is recomputed; `ReviewItem.resolved`.
- This keeps the system fast *and* trustworthy — auto-grade the clean majority, human-check only the doubtful minority.

## Test fixtures (for building the engine)

Build a labeled set of sample sheets with known answers covering:
- clean fills, faint/partial fills, double marks, stray pen marks, blanks,
- skewed/rotated/perspective phone photos, low light, shadows,
- damaged/missing QR, smudged fiducials.
Use these in automated tests to measure accuracy and verify the right items get flagged. Track auto-grade rate and error rate as quality metrics.

## Open items
- Final template dimensions / max questions per page / option counts to support (drives `page_map`).
- On-device detection approach for live auto-grab (which library / WASM build for QR + fiducial detection in the browser and in React Native).
- Confidence threshold values — calibrate empirically against the fixture set.
