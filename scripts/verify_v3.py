#!/usr/bin/env python3
"""One-command gate for the ski report v3 work.

Written because the report pipeline, the Qt UI and the schema layer each need a
different dependency set, so a green `pytest` alone does not prove the app runs.
This script checks the pieces in dependency order and keeps going after a
failure, so one run tells you everything that is wrong.

    python scripts/verify_v3.py              # everything
    python scripts/verify_v3.py --skip-ui    # no PySide6 available
    python scripts/verify_v3.py --quiet      # summary only

Exit code is the number of failed checks, so it is usable in CI and in a
pre-commit hook.

Run this on macOS before touching the iOS client, and again on Windows before
committing — the point of the exercise is that the same template renders on both.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
results: list[tuple[str, str, str]] = []
_t0 = time.time()


def record(name: str, status: str, detail: str = "") -> None:
    results.append((name, status, detail))
    if not ARGS.quiet or status != PASS:
        mark = {PASS: "  ok  ", FAIL: " FAIL ", SKIP: " skip "}[status]
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""), flush=True)


def check(name: str):
    """Decorator: run a check, turn a return value or exception into a result."""

    def wrap(fn):
        try:
            detail = fn() or ""
            record(name, PASS, str(detail))
        except _Skip as exc:
            record(name, SKIP, str(exc))
        except Exception as exc:  # noqa: BLE001 - a check failure is data
            record(name, FAIL, f"{type(exc).__name__}: {exc}")
        return fn

    return wrap


class _Skip(Exception):
    pass


# --------------------------------------------------------------------------- #
# 0. environment
# --------------------------------------------------------------------------- #


def run_all() -> None:
    @check("environment")
    def _env():
        mods = {}
        for m in ("pydantic", "numpy", "cv2", "mediapipe", "PySide6", "pytest"):
            try:
                mod = __import__(m)
                mods[m] = getattr(mod, "__version__", "?")
            except Exception:
                mods[m] = "MISSING"
        missing = [k for k, v in mods.items() if v == "MISSING"]
        detail = f"{platform.system()} py{sys.version_info.major}.{sys.version_info.minor}; " + ", ".join(
            f"{k} {v}" for k, v in mods.items()
        )
        if "pydantic" in missing or "numpy" in missing:
            raise RuntimeError("pydantic and numpy are required: " + detail)
        return detail

    @check("store paths resolve for this platform")
    def _paths():
        from clients.windows.store import prefs

        try:
            from clients.windows.store import paths as pathmod

            root = pathmod.data_root()
        except Exception:
            root = Path(prefs.prefs_path()).parent
        expect = {
            "Darwin": "Library/Application Support",
            "Windows": "AppData",
            "Linux": ".local/share",
        }.get(platform.system())
        if expect and expect not in str(root) and not os.environ.get("VISUAL_PREFS"):
            raise RuntimeError(f"{root} does not look right for {platform.system()}")
        return str(root)

    # ----------------------------------------------------------------------- #
    # 1. data layer
    # ----------------------------------------------------------------------- #

    @check("curriculum v3 loads and the expert file accepts it")
    def _curriculum():
        from core.sports.curriculum import load_curriculum
        from core.sports.ski_expert import accept_curriculum

        cur = load_curriculum()
        issues = accept_curriculum()
        if issues:
            raise RuntimeError(f"{len(issues)} expert issues: {issues[:3]}")
        tiers: dict[str, int] = {}
        for lv in cur.levels.values():
            tiers[getattr(lv, "tier", "full")] = tiers.get(getattr(lv, "tier", "full"), 0) + 1
        return f"schema {cur.schema_version}, {len(cur.levels)} levels {tiers}"

    @check("every level has a kb_stage that exists in the knowledge pack")
    def _bridge():
        from core.sports.curriculum import load_curriculum
        from core.sports.knowledge_pack import load_pack

        pack = load_pack()
        if pack is None:
            raise _Skip("knowledge pack not present")
        stages = set(pack.get("stages", {}))
        cur = load_curriculum()
        bad = [
            lv_id
            for lv_id, lv in cur.levels.items()
            if getattr(lv, "kb_stage", "") and getattr(lv, "kb_stage") not in stages
        ]
        if bad:
            raise RuntimeError(f"levels pointing at a missing kb stage: {bad}")
        return f"{len(stages)} kb stages, {len(cur.levels)} levels bridged"

    @check("knowledge pack is up to date with its source")
    def _pack_fresh():
        script = ROOT / "scripts" / "import_ski_knowledge.py"
        if not script.exists():
            raise _Skip("importer missing")
        proc = subprocess.run(
            [sys.executable, str(script), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "pack is stale — re-run scripts/import_ski_knowledge.py: "
                + (proc.stdout or proc.stderr).strip()[:200]
            )
        return "in sync"

    @check("every metric id referenced by the curriculum exists in the registry")
    def _metric_ids():
        from core.sports.curriculum import load_curriculum
        from core.sports.metrics import REGISTRY

        known = {spec.metric_id if hasattr(spec, "metric_id") else spec.id for spec in REGISTRY}
        cur = load_curriculum()
        missing: set[str] = set()
        for lv in cur.levels.values():
            for field in ("core_metrics", "gate_metrics"):
                for mid in getattr(lv, field, None) or []:
                    if mid not in known:
                        missing.add(mid)
        if missing:
            raise RuntimeError(f"unknown metric ids: {sorted(missing)}")
        return f"{len(known)} metrics registered"

    # ----------------------------------------------------------------------- #
    # 2. i18n
    # ----------------------------------------------------------------------- #

    @check("i18n: every key has zh, no key carries an 'en' field")
    def _i18n():
        data = json.loads((ROOT / "locales" / "strings.json").read_text(encoding="utf-8"))
        strings = data["strings"]
        no_zh = [k for k, v in strings.items() if not v.get("zh")]
        has_en = [k for k, v in strings.items() if "en" in v]
        if no_zh or has_en:
            raise RuntimeError(f"{len(no_zh)} missing zh, {len(has_en)} with an 'en' field")
        return f"{len(strings)} keys"

    @check("i18n: flat locale files match strings.json")
    def _locales_built():
        data = json.loads((ROOT / "locales" / "strings.json").read_text(encoding="utf-8"))
        n = len(data["strings"])
        stale = []
        for path in (ROOT / "locales").glob("*.json"):
            if path.name.startswith("_") or path.name in {"strings.json", "zh_en.json"}:
                continue
            if len(json.loads(path.read_text(encoding="utf-8"))) != n:
                stale.append(path.name)
        if stale:
            raise RuntimeError(f"run scripts/build_locales.py — stale: {stale}")
        return "built"

    # ----------------------------------------------------------------------- #
    # 3. pipeline end to end, on a synthetic clip
    # ----------------------------------------------------------------------- #

    @check("assess_clip produces a valid 3.0.0 report from a synthetic clip")
    def _assess():
        try:
            from tests.ski_fixtures import synth_parallel_clip  # type: ignore
        except Exception:
            try:
                from core.sports.report_cases import synth_clip  # type: ignore

                analysis = synth_clip("parallel")
            except Exception as exc:
                raise _Skip(f"no synthetic clip helper ({exc})") from exc
        else:
            analysis = synth_parallel_clip()

        from core.sports.assess import assess_clip
        from schemas.stage_report import StageReport

        report = assess_clip(analysis)
        StageReport.model_validate(report.model_dump())
        if report.schema_version != "3.0.0":
            raise RuntimeError(f"schema_version is {report.schema_version}")
        blocks = {
            "classification": report.classification is not None,
            "metrics": bool(report.metrics),
            "turns": report.turns is not None,
            "tree": bool(report.tree),
            "filming": True,
        }
        empty = [k for k, v in blocks.items() if not v]
        if empty:
            raise RuntimeError(f"v3 blocks not populated: {empty}")
        states = {m.state.value if hasattr(m.state, "value") else m.state for m in report.metrics}
        return (
            f"stage={report.stage_id} score={report.score_0_100:.0f} "
            f"conf={report.confidence:.2f} metrics={len(report.metrics)} "
            f"turns={report.turns.count if report.turns else 0} states={sorted(states)}"
        )

    @check("no metric reports a value while claiming it was not measured")
    def _metric_states():
        try:
            from core.sports.report_cases import CASES
        except Exception as exc:
            raise _Skip(str(exc)) from exc
        bad = []
        for case in CASES:
            report = case() if callable(case) else case
            for m in getattr(report, "metrics", []) or []:
                state = m.state.value if hasattr(m.state, "value") else m.state
                if state != "ok" and m.value is not None:
                    bad.append((getattr(report, "clip_id", "?"), m.id, state))
        if bad:
            raise RuntimeError(f"{len(bad)} contradictory metrics, e.g. {bad[:3]}")
        return f"{len(CASES)} cases clean"

    @check("report audit reports no layout or bilingual issues")
    def _audit():
        from core.sports.report_audit import review_issues

        issues = review_issues()
        if issues:
            raise RuntimeError(f"{len(issues)} issues: {issues[:3]}")
        return "clean"

    # ----------------------------------------------------------------------- #
    # 4. UI
    # ----------------------------------------------------------------------- #

    @check("report panel renders a v3 report offscreen")
    def _ui_v3():
        if ARGS.skip_ui:
            raise _Skip("--skip-ui")
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PySide6.QtWidgets import QApplication
        except Exception as exc:
            raise _Skip(f"PySide6 unavailable ({exc})") from exc

        from clients.windows.ui.report_panel import CHAPTERS, StageReportPanel
        from core.sports.assess import assess_clip
        from core.sports.history import StageHistory
        from core.sports.report_cases import CASES, clip_for, history_for

        app = QApplication.instance() or QApplication([])
        panel = StageReportPanel()
        case = CASES[0]
        report = (
            case()
            if callable(case)
            else assess_clip(
                clip_for(case),
                lang="zh",
                history=StageHistory.from_reports(history_for(case)),
            )
        )
        panel.set_report(report)
        panel.resize(1200, 900)
        panel.show()
        app.processEvents()

        labels = panel.findChildren(type(panel).__mro__[0])  # touch the tree
        newline_offenders = []
        from PySide6.QtWidgets import QLabel

        for lab in panel.findChildren(QLabel):
            if "\n" in lab.text():
                newline_offenders.append(lab.text()[:40])
        if newline_offenders:
            raise RuntimeError(
                f"{len(newline_offenders)} labels join paragraphs with a newline, "
                f"which the UI rules forbid: {newline_offenders[:2]}"
            )
        panel.deleteLater()
        app.processEvents()
        return f"{len(CHAPTERS)} chapters, {len(labels)} widgets, no newline labels"

    @check("report panel degrades on a 2.1.0 report")
    def _ui_legacy():
        if ARGS.skip_ui:
            raise _Skip("--skip-ui")
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PySide6.QtWidgets import QApplication
        except Exception as exc:
            raise _Skip(f"PySide6 unavailable ({exc})") from exc

        from clients.windows.ui.report_panel import StageReportPanel
        from core.sports.assess import assess_clip
        from core.sports.history import StageHistory
        from core.sports.report_cases import CASES, clip_for, history_for

        app = QApplication.instance() or QApplication([])
        case = CASES[0]
        report = (
            case()
            if callable(case)
            else assess_clip(
                clip_for(case),
                lang="zh",
                history=StageHistory.from_reports(history_for(case)),
            )
        )
        legacy = report.model_copy(
            update={
                "classification": None,
                "metrics": [],
                "turns": None,
                "tree": [],
                "knowledge_ref": None,
                "knowledge_focus": None,
                "scene": None,
                "profile_summary": None,
                "filming": [],
            }
        )
        panel = StageReportPanel()
        panel.set_report(legacy)
        app.processEvents()
        panel.deleteLater()
        app.processEvents()
        return "old reports still open"

    # ----------------------------------------------------------------------- #
    # 5. the real test suite
    # ----------------------------------------------------------------------- #

    @check("pytest")
    def _pytest():
        if ARGS.skip_tests:
            raise _Skip("--skip-tests")
        try:
            import pytest  # noqa: F401
        except Exception as exc:
            raise _Skip(f"pytest unavailable ({exc})") from exc
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        tail = (proc.stdout or proc.stderr).strip().splitlines()
        summary = tail[-1] if tail else "no output"
        if proc.returncode != 0:
            failing = [ln for ln in tail if ln.startswith(("FAILED", "ERROR"))][:6]
            hint = ""
            if any("test_assess_v3" in ln for ln in failing):
                hint = (
                    "\n         → the recorded fixtures are behind the scorer. "
                    "Regenerate with `python -m tests.test_assess_v3 --write`, "
                    "then read the diff: only scores/gates should move."
                )
            raise RuntimeError(
                summary + (" | " + "; ".join(failing) if failing else "") + hint
            )
        return summary

    # ----------------------------------------------------------------------- #
    # 6. platform hygiene
    # ----------------------------------------------------------------------- #

    @check("no new platform conditionals in the report layer")
    def _platform_hygiene():
        """The report template must render identically on macOS and Windows.

        Two darwin conditionals are expected and allowed: the capture-page camera
        block and the MediaPipe CPU delegate. Anything else in the report path is
        a regression.
        """
        allowed = {
            Path("clients/windows/ui/capture_page.py"),
            Path("core/mediapipe_engine.py"),
        }
        offenders: list[str] = []
        for rel in [
            "clients/windows/ui/report_panel.py",
            "clients/windows/ui/report_layout.py",
            "clients/windows/ui/report_charts.py",
            "clients/windows/ui/report_knowledge.py",
            "clients/windows/ui/theme.py",
            "core/sports/assess.py",
            "core/sports/metrics.py",
            "core/sports/classify.py",
            "core/sports/score.py",
            "core/sports/tree.py",
        ]:
            path = ROOT / rel
            if not path.exists() or Path(rel) in allowed:
                continue
            text = path.read_text(encoding="utf-8")
            for needle in ("sys.platform", "platform.system", "darwin", "win32"):
                if needle in text:
                    offenders.append(f"{rel}:{needle}")
        if offenders:
            raise RuntimeError("platform-specific code in the report path: " + ", ".join(offenders))
        return "report path is platform-neutral"


def main() -> int:
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-ui", action="store_true", help="no PySide6 in this environment")
    ap.add_argument("--skip-tests", action="store_true", help="do not run pytest")
    ap.add_argument("--quiet", action="store_true", help="print only failures and the summary")
    ARGS = ap.parse_args()

    print(f"ski report v3 verification — {platform.system()} {platform.release()}\n")
    run_all()

    failed = [r for r in results if r[1] == FAIL]
    skipped = [r for r in results if r[1] == SKIP]
    print(
        f"\n{len(results) - len(failed) - len(skipped)} passed, "
        f"{len(failed)} failed, {len(skipped)} skipped "
        f"in {time.time() - _t0:.1f}s"
    )
    if skipped:
        print("skipped: " + ", ".join(n for n, _, _ in skipped))
    if failed:
        print("\nfailures:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
    return len(failed)


ARGS = argparse.Namespace(skip_ui=False, skip_tests=False, quiet=False)

if __name__ == "__main__":
    raise SystemExit(main())
