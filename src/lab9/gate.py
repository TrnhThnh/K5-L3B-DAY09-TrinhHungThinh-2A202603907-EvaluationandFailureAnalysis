"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from math import isfinite
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    graded = {m["id"] for m in spec["metrics"] if m["id"] in GRADERS}
    graded.update(s["metric"] for s in spec.get("slices", ()))
    pairs = []
    for name, report in (("PR", pr), ("baseline", base)):
        manifest, rows = report["manifest"], report["rows"]
        keys = {(row["item_id"], row["seed"]) for row in rows}
        items = {item for item, _ in keys}
        seeds = set(manifest["seeds"])
        if (not rows or len(items) != manifest["items"] or len(seeds) != len(manifest["seeds"])
                or len(keys) != len(rows) or keys != {(item, seed) for item in items for seed in seeds}):
            problems.append(f"{name}: incomplete or duplicate item/seed rows")
        if report.get("evaluator_failures"):
            problems.append(f"{name}: evaluator failures")
        for metric, value in report["metrics"].items():
            if value is not None and (not isinstance(value, (int, float)) or not isfinite(value)):
                problems.append(f"{name}: invalid aggregate {metric}")
        invalid = [metric for metric in sorted(graded)
                   if any(type(row.get(metric)) is not bool for row in rows)]
        if invalid:
            problems.append(f"{name}: invalid or missing row scores for {', '.join(invalid)}")
        elif rows and ("shape" in report or any("cost" in row for row in rows)):
            if any(not isinstance(row.get("cost"), (int, float)) or not isfinite(row["cost"])
                   or row["cost"] < 0 for row in rows):
                problems.append(f"{name}: invalid trial cost")
            else:
                computed = aggregate(rows, sorted(graded), k_values=spec.get("pass_k", []))
                mismatches = [mid for mid, value in computed.items() if report["metrics"].get(mid) != value]
                if mismatches:
                    problems.append(f"{name}: aggregates disagree with rows: {', '.join(mismatches)}")
        pairs.append({(row["item_id"], row["seed"]): set(row.get("slices") or []) for row in rows})
    if pairs[0].keys() != pairs[1].keys():
        problems.append("PR and baseline item/seed pairs differ")
    elif pairs[0] != pairs[1]:
        problems.append("PR and baseline slice tags differ")
    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        for section, keys in (("metrics", ("id",)), ("slices", ("name", "metric"))):
            current = {tuple(entry[key] for key in keys): entry for entry in spec.get(section, [])}
            for old in base_spec.get(section, []):
                identity = tuple(old[key] for key in keys)
                new = current.get(identity)
                if new is None:
                    problems.append(f"ratchet: removed {section} {'/'.join(identity)}")
                    continue
                before, after = (old, new) if section == "slices" else (
                    old.get("threshold", {}), new.get("threshold", {}))
                relaxed = (old.get("blocking") and not new.get("blocking")
                           or before.get("no_significant_drop") and not after.get("no_significant_drop")
                           or "min" in before and ("min" not in after or after["min"] < before["min"])
                           or any(key in before and (key not in after or after[key] > before[key])
                                  for key in ("max", "max_increase")))
                if relaxed:
                    problems.append(f"ratchet: loosened {'/'.join(identity)}")
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    for rule in spec.get("slices", []):
        name, metric = rule["name"], rule["metric"]
        ident = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        failed = not a or a.keys() != b.keys()
        value = sum(a.values()) / len(a) if a else None
        note = ""
        if not failed:
            failed = "min" in rule and value < rule["min"]
            if rule.get("no_significant_drop"):
                delta, lo, hi = _paired(a, b, spec)
                failed |= hi < 0
                note = f" Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
        if failed and rule.get("blocking"):
            blocked.append(ident)
        verdict = ("BLOCK" if rule.get("blocking") else "warn") if failed else "ok"
        shown = f"{value:.4f}" if value is not None else "missing"
        lines.append(f"  {ident} {shown}{note} {verdict}")
    return blocked, lines


def _paired(a: dict[str, float], b: dict[str, float], spec: dict) -> tuple[float, float, float]:
    bs = spec.get("bootstrap", {})
    keys = sorted(a.keys() & b.keys())
    return stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                  n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                  confidence=bs.get("confidence", 0.95))


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            d, lo, hi = _paired(a, b, spec)
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
