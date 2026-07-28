"""
omr.bench — a measurable accuracy and latency benchmark for the scan pipeline.

Run it:

    python manage.py scan_bench                 # all cases
    python manage.py scan_bench --case low_light --save /tmp/shots

Why this exists
---------------
Every claim about the reader ("handles blur", "works in low light") is
unfalsifiable without a fixed corpus and a single number. This builds a real
sheet with the product's own generator, applies known capture damage, and
checks the decoded answers against the ground truth that produced them.

What it does NOT cover
----------------------
No real camera, no real printer, no real paper. Blur here is a convolution, not
an out of focus lens; noise is Gaussian, not a sensor's. Passing this is
necessary, not sufficient. A physical print, fill and photograph round trip is
still required before trusting a score in a classroom.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from omr.geometry import build_template
from omr.scan import degrade as dg
from omr.simulate import render_canonical_image

N_QUESTIONS = 30
N_OPTIONS = 4
ROLL_DIGITS = 3
ROLL = "007"

SHEET_META = {
    "sheet_code": "bench0001-BENCHMRK",
    "human_readable_code": "BENCHMRK",
    "institution": "Benchmark School",
    "test_title": "Benchmark Test",
    "student_name": "Test Student",
    "roll_number": ROLL,
}


@dataclass
class CaseResult:
    name: str
    n: int = 0
    aligned: int = 0
    qr_ok: int = 0
    exact: int = 0          # every answer on the page correct
    refused: int = 0        # sheet-level flag: not graded, sent to review
    q_total: int = 0
    q_correct: int = 0
    wrong_confident: int = 0  # answered, wrong, and NOT flagged. The dangerous one.
    flagged: int = 0
    ms: list = field(default_factory=list)

    @property
    def align_rate(self):  return self.aligned / self.n if self.n else 0.0
    @property
    def graded(self):      return self.n - self.refused
    @property
    def exact_rate(self):  return self.exact / self.graded if self.graded else 0.0
    @property
    def read_rate(self):   return self.graded / self.n if self.n else 0.0
    @property
    def q_rate(self):      return self.q_correct / self.q_total if self.q_total else 0.0
    @property
    def p50(self):         return float(np.percentile(self.ms, 50)) if self.ms else 0.0
    @property
    def p95(self):         return float(np.percentile(self.ms, 95)) if self.ms else 0.0


def build_bench_sheet(rng, *, ink=dg.INK_BIRO, style="fill", coverage=0.75):
    """Render one sheet with known marks. Returns (image, descriptor, truth)."""
    descriptor = build_template(
        num_questions=N_QUESTIONS, num_options=N_OPTIONS, roll_digits=ROLL_DIGITS
    )
    img = render_canonical_image(descriptor, SHEET_META, 0, scale=2.0)

    labels = [chr(ord("A") + i) for i in range(N_OPTIONS)]
    truth: dict[int, list[str]] = {}

    by_q = {}
    for entry in descriptor["answer_bubbles"]:
        if entry["page"] != 0:
            continue
        by_q[entry["q_pos"]] = {o["label"]: (o["cx"], o["cy"], o["r"]) for o in entry["options"]}

    for q_pos, opts in by_q.items():
        label = labels[int(rng.integers(0, N_OPTIONS))]
        truth[q_pos] = [label]
        cx, cy, r = opts[label]
        dg.mark_bubble(
            img, cx * 2.0, cy * 2.0, r * 2.0,
            style=style, ink=ink, coverage=coverage,
            offset=(float(rng.normal(0, 0.06)), float(rng.normal(0, 0.06))),
            rng=rng,
        )

    rg = descriptor["roll_grid"]
    for col, ch in enumerate(ROLL):
        if col >= rg["cols"]:
            break
        d = int(ch)
        cx = rg["origin"][0] + col * rg["col_pitch"]
        cy = rg["origin"][1] + d * rg["row_pitch"]
        dg.mark_bubble(img, cx * 2.0, cy * 2.0, rg["radius"] * 2.0,
                       style="fill", ink=ink, coverage=0.75, rng=rng)

    return img, descriptor, truth


# ---------------------------------------------------------------------------
# The corpus. Each case is (name, mark kwargs, capture function).
# ---------------------------------------------------------------------------

def _cases():
    def ident(im, rng): return im

    def defocus(im, rng):  return dg.cap_defocus(im, sigma=2.4)
    def motion(im, rng):   return dg.cap_motion(im, length=17, angle_deg=25)
    def lowlight(im, rng): return dg.cap_noise(dg.cap_low_light(im, gain=0.30, gamma=1.7), 10, rng)
    def shadow(im, rng):   return dg.cap_shadow(im, strength=0.6, angle_deg=35)
    def vignette(im, rng): return dg.cap_vignette(im, strength=0.5)
    def jpeg(im, rng):     return dg.cap_jpeg(im, quality=35)
    def upside(im, rng):   return dg.cap_rotate180(im)
    def small(im, rng):    return dg.cap_resize(im, 0.45)

    def desk_white(im, rng):
        return dg.cap_on_surface(im, surface=235, keystone=0.0, rng=rng)

    def desk_wood(im, rng):
        return dg.cap_on_surface(im, surface=90, keystone=0.0, rng=rng)

    def desk_dark(im, rng):
        return dg.cap_on_surface(im, surface=40, keystone=0.0, rng=rng)

    def handheld(im, rng):
        return dg.cap_on_surface(im, surface=120, keystone=0.18, rotate_deg=3.0, rng=rng)

    def worst(im, rng):
        """Everything a real bad capture does at once."""
        im = dg.cap_on_surface(im, surface=70, keystone=0.22, rotate_deg=-4.0, rng=rng)
        im = dg.cap_shadow(im, strength=0.5, angle_deg=20)
        im = dg.cap_low_light(im, gain=0.42, gamma=1.45)
        im = dg.cap_defocus(im, sigma=1.8)
        im = dg.cap_motion(im, length=9, angle_deg=10)
        im = dg.cap_vignette(im, strength=0.35)
        im = dg.cap_noise(im, sigma=9, rng=rng)
        return dg.cap_jpeg(im, quality=40)

    heavy = dict(ink=dg.INK_HEAVY_BIRO)
    biro = dict(ink=dg.INK_BIRO)
    hb = dict(ink=dg.INK_PENCIL_HB)
    light = dict(ink=dg.INK_PENCIL_LIGHT)
    faint = dict(ink=dg.INK_PENCIL_FAINT)

    return [
        ("clean",            biro,  ident),
        ("pencil_hb",        hb,    ident),
        ("pencil_light",     light, ident),
        ("pencil_faint",     faint, ident),
        ("tick_not_fill",    dict(ink=dg.INK_BIRO, style="tick"), ident),
        ("partial_fill",     dict(ink=dg.INK_PENCIL_HB, coverage=0.42), ident),
        ("defocus",          biro,  defocus),
        ("motion_blur",      biro,  motion),
        ("low_light",        hb,    lowlight),
        ("shadow",           hb,    shadow),
        ("vignette",         hb,    vignette),
        ("jpeg_artifacts",   biro,  jpeg),
        ("upside_down",      biro,  upside),
        ("low_resolution",   biro,  small),
        ("desk_white",       biro,  desk_white),
        ("desk_wood",        biro,  desk_wood),
        ("desk_dark",        biro,  desk_dark),
        ("handheld_angle",   biro,  handheld),
        ("worst_case",       hb,    worst),
        ("worst_case_pencil", light, worst),
    ]


def run(n_per_case: int = 5, only: str | None = None, save_dir: str | None = None,
        process=None) -> dict[str, CaseResult]:
    """
    Execute the benchmark. ``process`` defaults to the live pipeline so this
    always measures what the product actually ships.
    """
    if process is None:
        from omr.scan.pipeline import process_image as process

    import cv2

    results: dict[str, CaseResult] = {}
    for name, mark_kw, cap in _cases():
        if only and only != name:
            continue
        res = CaseResult(name=name)
        for i in range(n_per_case):
            rng = np.random.default_rng(1000 + i)
            img, descriptor, truth = build_bench_sheet(rng, **mark_kw)
            damaged = cap(img, rng)
            if save_dir and i == 0:
                cv2.imwrite(f"{save_dir}/{name}.png", damaged)

            t0 = time.perf_counter()
            try:
                out = process(damaged, descriptor)
            except Exception:
                out = None
            res.ms.append((time.perf_counter() - t0) * 1000.0)
            res.n += 1

            if not out:
                # A crash is a refusal too, just an impolite one.
                res.refused += 1
                continue
            flags = out.get("flags", []) or []
            if "no_qr" not in flags:
                res.qr_ok += 1
            if "alignment" not in flags and out.get("reads"):
                res.aligned += 1

            # A sheet-level flag means the pipeline declined to grade and sent
            # the sheet to review. That is the CORRECT outcome for an
            # unreadable capture, so it must not be scored as silently wrong.
            # Counting it that way conflates "refused honestly" with "graded
            # confidently and got it wrong", which are opposite behaviours.
            if {"no_qr", "alignment", "all_blank"} & set(flags):
                res.refused += 1
                continue

            reads = out.get("reads") or {}
            per_q_ok = True
            for q_pos, want in truth.items():
                res.q_total += 1
                entry = reads.get(q_pos) or reads.get(str(q_pos)) or {}
                got = entry.get("marked", [])
                flag = entry.get("flag")
                if flag:
                    res.flagged += 1
                if sorted(got) == sorted(want):
                    res.q_correct += 1
                else:
                    per_q_ok = False
                    # Wrong AND unflagged is the failure that reaches a student.
                    if not flag:
                        res.wrong_confident += 1
            if per_q_ok:
                res.exact += 1
        results[name] = res
    return results


def format_report(results: dict[str, CaseResult]) -> str:
    lines = []
    head = (f"{'case':<20}{'read':>6}{'exact':>7}{'answers':>9}"
            f"{'unflagged':>11}{'p50 ms':>9}{'p95 ms':>9}")
    lines.append(head)
    lines.append("-" * len(head))
    tot_q = tot_ok = tot_bad = 0
    for r in results.values():
        lines.append(
            f"{r.name:<20}{r.read_rate:>6.0%}{r.exact_rate:>7.0%}"
            f"{r.q_rate:>9.1%}{r.wrong_confident:>11d}{r.p50:>9.1f}{r.p95:>9.1f}"
        )
        tot_q += r.q_total
        tot_ok += r.q_correct
        tot_bad += r.wrong_confident
    lines.append("-" * len(head))
    overall = tot_ok / tot_q if tot_q else 0.0
    lines.append(f"{'OVERALL':<20}{'':>7}{'':>7}{overall:>9.1%}{tot_bad:>11d}")
    lines.append("")
    n_all = sum(r.n for r in results.values())
    n_graded = sum(r.graded for r in results.values())
    lines.append(f"{'read rate':<20}{n_graded / n_all if n_all else 0:>6.0%}"
                 f"   ({n_graded} of {n_all} sheets graded, rest sent to review)")
    lines.append("")
    lines.append("read       sheets the pipeline was willing to grade at all")
    lines.append("exact      of those graded, every answer matched the truth")
    lines.append("answers    per question accuracy over graded sheets")
    lines.append("unflagged  graded, WRONG, and not flagged for review. Target is 0.")
    lines.append("")
    lines.append("A refused sheet is a SAFE outcome: the teacher re-scans it.")
    lines.append("An unflagged wrong answer is the only truly bad one.")
    return "\n".join(lines)
