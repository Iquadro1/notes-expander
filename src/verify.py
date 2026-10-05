"""Verify a rendered lesson HTML (Step 4 helper).

    uv run verify-html output/<course>/01.md  # accepts .md or .html
    uv run verify-html output/<course>/01.html --no-browser --strict

Checks (no LLM vision needed):
- HTML exists (deriving .html from .md when given a Markdown path).
- Freshness: HTML newer than templates/layout.html and src/render.py.
- Markers: counts source/ref/missing sections; missing files fail.
- Assets: every data-src / data-base PNG exists on disk.
- No MathZzZ token leftovers, no polyfill.io reference.
- Inline viewer JS passes `node --check` (when node exists).
- Browser (unless --no-browser): chromium headless hover test via
  scripts/verify-hover.js (needs puppeteer-core; SKIP when unavailable):
  sections render, hovering swaps the viewer image/box/chip, no console errors.

Exit 1 on errors, or on warnings with --strict.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote

TEMPLATE = Path("templates/layout.html")
RENDER_SRC = Path("src/render.py")
HOVER_SCRIPT = Path("scripts/verify-hover.js")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify rendered lesson HTML")
    parser.add_argument("target", help=".html file (or .md, resolved to its .html)")
    parser.add_argument("--course", default=None, help="Course slug (only used for messages)")
    parser.add_argument("--shots", default="/tmp/opencode",
                        help="Screenshot dir for the browser check")
    parser.add_argument("--no-browser", action="store_true", help="Skip chromium hover test")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 on warnings as well as errors")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    target = Path(args.target)
    html = target.with_suffix(".html") if target.suffix == ".md" else target
    if not html.is_file():
        print(f"ERROR: {html} does not exist — run render-html first.")
        raise SystemExit(1)

    # Freshness (the Oct stale-build bug: HTML older than template/renderer).
    for dep in (TEMPLATE, RENDER_SRC):
        if dep.is_file() and html.stat().st_mtime < dep.stat().st_mtime:
            errors.append(f"STALE: {html} older than {dep} — re-run render-html.")

    text = html.read_text(encoding="utf-8", errors="replace")

    kinds = re.findall(r'data-kind="([a-z]+)"', text)
    n_sections = len(kinds)
    n_missing = kinds.count("missing")
    print(f"Sections: {n_sections} "
          f"(pages/image/doc/link/none/missing: "
          f"{kinds.count('pages')}/{kinds.count('page') + kinds.count('image')}/"
          f"{kinds.count('doc')}/{kinds.count('link')}/{kinds.count('none')}/{n_missing})")
    if n_sections == 0:
        errors.append("No viewer sections found (no [source:]/[ref:] markers?).")
    if n_missing:
        titles = sorted(set(re.findall(r'data-title="([^"]+)"', text)))
        errors.append(f"{n_missing} missing-file marker(s): {', '.join(titles[:5])}")

    if "MathZzZ" in text:
        errors.append("Math token leftover (MathZzZ) — math restore failed.")
    if "polyfill.io" in text:
        errors.append("polyfill.io reference present (dead/hostile domain).")

    # Assets referenced by markers must exist on disk (relative to the HTML).
    refs = set(re.findall(r'data-src="([^"]+)"', text))
    bases = set(re.findall(r'data-base="([^"]+)"', text))
    counts = dict(re.findall(r'data-base="([^"]+)"[^>]*data-count="(\d+)"', text))
    checked = 0
    for ref in refs:
        p = (html.parent / unquote(ref)).resolve()
        checked += 1
        if not p.is_file():
            errors.append(f"Asset missing: {ref} (-> {p})")
    for base in bases:
        try:
            total = int(counts.get(base, "1"))
        except ValueError:
            total = 1
        for i in (1, total):
            probe = f"{base}-{i}.png"
            p = (html.parent / unquote(probe)).resolve()
            checked += 1
            if not p.is_file():
                errors.append(f"Asset missing: {probe} (-> {p})")
                break
    print(f"Assets checked: {checked} reference(s).")

    # Inline viewer JS syntax (skip gracefully without node).
    if shutil.which("node"):
        m = re.findall(r"<script>(.*?)</script>", text, re.S)
        inline = max(m, key=len) if m else ""
        if inline.strip():
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
                fh.write(inline)
                tmp = fh.name
            try:
                r = subprocess.run(["node", "--check", tmp],
                                   capture_output=True, text=True, timeout=30)
                if r.returncode == 0:
                    print("JS: inline viewer script OK (node --check).")
                else:
                    errors.append(f"JS syntax error: {(r.stderr or r.stdout).strip()[:300]}")
            finally:
                Path(tmp).unlink(missing_ok=True)
    else:
        warnings.append("node not found — JS syntax check skipped.")

    # Browser hover test (skip gracefully without chromium/puppeteer).
    if not args.no_browser:
        chromium = (shutil.which("chromium") or shutil.which("chromium-browser")
                     or shutil.which("google-chrome") or shutil.which("google-chrome-stable"))
        if not chromium:
            warnings.append("no chromium binary — browser hover check skipped.")
        elif not HOVER_SCRIPT.is_file():
            warnings.append(f"{HOVER_SCRIPT} missing — browser check skipped.")
        elif not shutil.which("node"):
            warnings.append("node not found — browser check skipped.")
        else:
            shots = Path(args.shots)
            shots.mkdir(parents=True, exist_ok=True)
            r = subprocess.run(["node", str(HOVER_SCRIPT), str(html.resolve()), str(shots)],
                               capture_output=True, text=True, timeout=120)
            try:
                # The script prints exactly one JSON object.
                payload = json.loads(r.stdout[r.stdout.index("{"):r.stdout.rindex("}") + 1])
            except (ValueError, IndexError):
                errors.append(f"Browser check crashed: {(r.stderr or r.stdout).strip()[:300]}")
                payload = None
            if payload is not None:
                status = payload.get("status")
                if status == "SKIP":
                    warnings.append(f"browser check skipped: {payload.get('reason')}")
                else:
                    print(f"Browser: {payload.get('sections', '?')} sections, "
                          f"{len(payload.get('hovers', []))} hover(s) sampled "
                          f"→ shots in {shots}")
                    for h in payload.get("hovers", []):
                        print(f"  hover {h['idx']}: img={h['img']} box={h['box']} "
                              f"page={h['pageLabel']} chip={h['chip'][:60]}")
                    for e in payload.get("consoleErrors", []):
                        errors.append(f"Console error: {e[:200]}")
                    if status == "ERROR":
                        errors.append(f"Browser check: {payload.get('reason', '')[:200]}")
    else:
        print("Browser check skipped (--no-browser).")

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  WARNING: {w}")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  ERROR: {e}")
        raise SystemExit(1)
    if warnings and args.strict:
        raise SystemExit(1)
    print("VERIFY OK." if not warnings else "VERIFY OK (with skipped checks).")


if __name__ == "__main__":
    main()
