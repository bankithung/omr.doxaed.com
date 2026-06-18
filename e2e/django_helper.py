"""
e2e/django_helper.py — backend helpers for the browser E2E run.

Run with the backend venv python from anywhere:
    backend/.venv/Scripts/python.exe e2e/django_helper.py token <email>
    backend/.venv/Scripts/python.exe e2e/django_helper.py make-scans <test_id> <out_dir>

Subcommands
-----------
token <email>
    Print JSON {"uid","token","verify_path"} — the SAME uid/token the
    verification email contains (regenerated via Django's token generator).
    Lets the browser navigate straight to the verify URL, faithfully
    reproducing "user clicks the email link".

make-scans <test_id> <out_dir>
    For every OmrSheet of the test, render a synthetic *filled* scan PNG
    (perfect score, except every 3rd sheet drops one answer for score
    variety so analytics aren't degenerate). Drives the REAL CV pipeline.
    Prints a JSON manifest: [{sheet_id, roll, files:[...], expected_correct,
    n_questions, perturbed}].
"""
import json
import os
import sys

# --- Django bootstrap -------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.join(os.path.dirname(_HERE), "backend")
sys.path.insert(0, _BACKEND)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()


def cmd_token(email):
    from accounts.tokens import make_uid_token
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.get(email=email)
    uid, token = make_uid_token(user)
    print(json.dumps({
        "uid": uid,
        "token": token,
        "verify_path": f"/verify-email?uid={uid}&token={token}",
        "is_email_verified": user.is_email_verified,
    }))


def cmd_latest_ids(email):
    """Newest class/test/roster ids owned by the user (solo scope)."""
    from assessments.models import ClassGroup, Test
    from django.contrib.auth import get_user_model
    from rosters.models import Roster

    User = get_user_model()
    user = User.objects.get(email=email)
    cg = ClassGroup.objects.filter(user=user).order_by("-id").first()
    test = Test.objects.filter(user=user).order_by("-id").first()
    roster = Roster.objects.filter(user=user).order_by("-id").first()
    print(json.dumps({
        "class_id": cg.id if cg else None,
        "test_id": test.id if test else None,
        "roster_id": roster.id if roster else None,
        "test_title": test.title if test else None,
    }))


def cmd_make_scans(test_id, out_dir):
    import cv2
    from omr.models import OmrSheet
    from omr.scan.pipeline import simulate_correct_marks
    from omr.simulate import simulate_scan

    os.makedirs(out_dir, exist_ok=True)
    sheets = (
        OmrSheet.objects.filter(test_id=test_id)
        .select_related("student", "test")
        .order_by("id")
    )
    manifest = []
    for idx, sheet in enumerate(sheets):
        descriptor = sheet.template_descriptor
        roll_cols = descriptor["roll_grid"]["cols"]
        roll = (sheet.student.roll_number or "0")[:roll_cols]

        marked = simulate_correct_marks(sheet)
        n_questions = len(sheet.answer_key)
        perturbed = (idx % 3 == 2) and n_questions > 1
        if perturbed:
            # Leave question position 0 blank → one wrong answer.
            marked = {k: v for k, v in marked.items() if k != 0}
        expected_correct = n_questions - (1 if perturbed else 0)

        try:
            student_name = sheet.student.full_name or "Student"
        except Exception:
            student_name = "Student"

        sheet_meta = {
            "sheet_code": sheet.sheet_code,
            "human_readable_code": sheet.human_readable_code,
            "institution": "E2E Academy",
            "test_title": sheet.test.title,
            "subject": sheet.test.subject or "",
            "student_name": student_name,
            "roll_label": "Roll No.",
            "roll_digits": roll_cols,
        }

        files = []
        page_count = descriptor.get("page_count", 1)
        for page in range(page_count):
            img = simulate_scan(
                descriptor, sheet_meta, marked=marked,
                roll=roll, page=page, scale=2.0,
            )
            ok, buf = cv2.imencode(".png", img)
            if not ok:
                raise RuntimeError(f"imencode failed for sheet {sheet.id} page {page}")
            fname = f"sheet_{sheet.id}_p{page}.png"
            fpath = os.path.join(out_dir, fname)
            with open(fpath, "wb") as fh:
                fh.write(buf.tobytes())
            files.append(os.path.abspath(fpath))

        manifest.append({
            "sheet_id": sheet.id,
            "roll": roll,
            "files": files,
            "expected_correct": expected_correct,
            "n_questions": n_questions,
            "perturbed": perturbed,
        })

    print(json.dumps(manifest))


def cmd_make_scan_tampered(test_id, out_dir):
    """Render ONE synthetic scan of the test's first sheet but with a WRONG roll
    (each digit shifted +1 mod 10) — correct answers, valid QR. Used to prove the
    Mode B roll reconciliation raises roll_mismatch while QR identity still holds.
    Prints {sheet_id, file, real_roll, tampered_roll}."""
    import cv2
    from omr.models import OmrSheet
    from omr.scan.pipeline import simulate_correct_marks
    from omr.simulate import simulate_scan

    os.makedirs(out_dir, exist_ok=True)
    sheet = (
        OmrSheet.objects.filter(test_id=test_id)
        .select_related("student", "test")
        .order_by("id")
        .first()
    )
    if sheet is None:
        print(json.dumps({}))
        return
    descriptor = sheet.template_descriptor
    roll_cols = descriptor["roll_grid"]["cols"]
    real_roll = (sheet.student.roll_number or "0").zfill(roll_cols)[:roll_cols]
    # Tamper: shift each digit +1 mod 10 -> a different, valid, same-width roll.
    tampered = "".join(str((int(c) + 1) % 10) if c.isdigit() else c for c in real_roll)

    marked = simulate_correct_marks(sheet)
    sheet_meta = {
        "sheet_code": sheet.sheet_code,
        "human_readable_code": sheet.human_readable_code,
        "institution": "E2E Academy",
        "test_title": sheet.test.title,
        "subject": sheet.test.subject or "",
        "student_name": sheet.student.full_name or "Student",
        "roll_label": "Roll No.",
        "roll_digits": roll_cols,
    }
    img = simulate_scan(descriptor, sheet_meta, marked=marked, roll=tampered, page=0, scale=2.0)
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("imencode failed")
    fpath = os.path.abspath(os.path.join(out_dir, f"tampered_{sheet.id}.png"))
    with open(fpath, "wb") as fh:
        fh.write(buf.tobytes())
    print(json.dumps({
        "sheet_id": sheet.id, "file": fpath,
        "real_roll": real_roll, "tampered_roll": tampered,
    }))


def main():
    if len(sys.argv) < 2:
        print("usage: django_helper.py {token <email> | latest-ids <email> | "
              "make-scans <test_id> <out_dir> | make-scan-tampered <test_id> <out_dir>}",
              file=sys.stderr)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "token":
        cmd_token(sys.argv[2])
    elif cmd == "latest-ids":
        cmd_latest_ids(sys.argv[2])
    elif cmd == "make-scans":
        cmd_make_scans(int(sys.argv[2]), sys.argv[3])
    elif cmd == "make-scan-tampered":
        cmd_make_scan_tampered(int(sys.argv[2]), sys.argv[3])
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
