#!/usr/bin/env python3
"""unvibecode-watch — turn two UnvibeCode runs into a pull-request comment.

UnvibeCode answers "what is this repository?", which a developer asks once per
repository. This turns the same artifacts into an answer to "what did this change
do?", which they ask on every pull request.

It does not re-implement any analysis. It reads the files `unvibecode review`
already writes:

    <run>/report-support/business-workflows.html   business workflow names
    <run>/*repository-context.zip                  chunks.jsonl, connections.jsonl
    <run>/technical-logs/analysis-status.json      per-component completion state

Stdlib only, matching the UnvibeCode client's own zero-dependency choice.

    python unvibecode_watch.py diff BASELINE_RUN HEAD_RUN
    python unvibecode_watch.py check RUN

A RUN is either an analysis folder (`<repo>-unvibecode-analysis-<timestamp>`) or
an `unvibecode_results` folder, in which case the most recent analysis is used.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import zipfile
from dataclasses import dataclass, field
from html.parser import HTMLParser


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

class _WorkflowTitleParser(HTMLParser):
    """Collect text inside <h3 class="workflow-title">...</h3>."""

    def __init__(self) -> None:
        super().__init__()
        self.titles: list[str] = []
        self._depth = 0
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "h3":
            classes = dict(attrs).get("class") or ""
            if "workflow-title" in classes.split():
                self._depth = 1
                self._buf = []
        elif self._depth:
            self._depth += 1

    def handle_endtag(self, tag):
        if not self._depth:
            return
        self._depth -= 1
        if self._depth == 0:
            title = " ".join("".join(self._buf).split())
            if title:
                self.titles.append(title)

    def handle_data(self, data):
        if self._depth:
            self._buf.append(data)


@dataclass
class Run:
    """One UnvibeCode analysis folder, loaded into comparable sets."""

    path: str
    label: str
    workflows: list[str] = field(default_factory=list)
    files: set[str] = field(default_factory=set)
    symbols: set[str] = field(default_factory=set)
    connections: set[tuple] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)
    has_workflow_map: bool = False


def resolve_run(path: str) -> str:
    """Accept an analysis folder, or a results folder holding several."""
    if os.path.isfile(os.path.join(path, "technical-logs", "analysis-status.json")):
        return path
    candidates = [p for p in glob.glob(os.path.join(path, "*")) if os.path.isdir(p)]
    analyses = [p for p in candidates if "-unvibecode-analysis-" in os.path.basename(p)]
    if not analyses:
        raise SystemExit(f"No UnvibeCode analysis folder found under: {path}")
    return max(analyses, key=os.path.getmtime)


def load_run(path: str, label: str) -> Run:
    run = Run(path=resolve_run(path), label=label)

    workflow_html = os.path.join(run.path, "report-support", "business-workflows.html")
    if os.path.isfile(workflow_html):
        run.has_workflow_map = True
        parser = _WorkflowTitleParser()
        with open(workflow_html, encoding="utf-8", errors="replace") as handle:
            parser.feed(handle.read())
        run.workflows = parser.titles

    bundles = glob.glob(os.path.join(run.path, "*repository-context.zip"))
    if bundles:
        with zipfile.ZipFile(bundles[0]) as bundle:
            for line in bundle.read("chunks.jsonl").decode("utf-8").splitlines():
                chunk = json.loads(line)
                path_ = chunk.get("file")
                if path_:
                    run.files.add(path_)
                name = chunk.get("qualified_name")
                if path_ and name:
                    run.symbols.add(f"{path_}::{name} ({chunk.get('kind', '?')})")
            for line in bundle.read("connections.jsonl").decode("utf-8").splitlines():
                edge = json.loads(line)
                run.connections.add((
                    edge.get("source_file"),
                    edge.get("relationship"),
                    edge.get("target_file"),
                    edge.get("symbol"),
                ))
            manifest = json.loads(bundle.read("manifest.json"))
            skipped = manifest.get("skipped_files") or []
            if skipped:
                run.warnings.append(
                    f"{len(skipped)} file(s) were skipped during analysis: "
                    + ", ".join(map(str, skipped[:5]))
                )

    run.warnings.extend(coverage_warnings(run.path))
    return run


def coverage_warnings(run_path: str) -> list[str]:
    """Surface components the engine did not actually complete.

    A run can report success while a headline deliverable was never produced.
    Reading analysis-status.json is the only way to tell, so the check belongs
    in CI rather than in a human's memory.
    """
    status_path = os.path.join(run_path, "technical-logs", "analysis-status.json")
    if not os.path.isfile(status_path):
        return ["No analysis-status.json found; completion state unknown."]

    with open(status_path, encoding="utf-8") as handle:
        status = json.load(handle)

    warnings: list[str] = []
    for lane_name, lane in (status.get("lanes") or {}).items():
        for component, state in (lane.get("components") or {}).items():
            if state != "COMPLETED":
                pretty = component.replace("_", " ")
                reason = lane.get("review_outcome") or lane.get("customer_reason")
                detail = f" (reason: {reason})" if reason else " (no reason given)"
                warnings.append(f"`{pretty}` was not produced — state `{state}`{detail}.")
        if lane.get("status") not in {"COMPLETED", None}:
            warnings.append(f"Lane `{lane_name}` finished as `{lane.get('status')}`.")

    overall = status.get("overall_status")
    if warnings and overall == "COMPLETE":
        warnings.append(
            "The run reports `overall_status: COMPLETE` despite the above, so a "
            "missing deliverable is not visible without reading this file."
        )
    return warnings


# --------------------------------------------------------------------------
# Diffing and rendering
# --------------------------------------------------------------------------

def diff_runs(base: Run, head: Run) -> dict:
    def delta(before: set, after: set) -> dict:
        return {"added": sorted(after - before), "removed": sorted(before - after)}

    return {
        "workflows": delta(set(base.workflows), set(head.workflows)),
        "files": delta(base.files, head.files),
        "symbols": delta(base.symbols, head.symbols),
        "connections": {
            key: [list(item) for item in value]
            for key, value in delta(base.connections, head.connections).items()
        },
        "totals": {
            "base": {"files": len(base.files), "symbols": len(base.symbols),
                     "connections": len(base.connections), "workflows": len(base.workflows)},
            "head": {"files": len(head.files), "symbols": len(head.symbols),
                     "connections": len(head.connections), "workflows": len(head.workflows)},
        },
        "warnings": {"base": base.warnings, "head": head.warnings},
    }


def _bullets(items: list[str], limit: int = 10) -> list[str]:
    lines = [f"- `{item}`" for item in items[:limit]]
    if len(items) > limit:
        lines.append(f"- …and {len(items) - limit} more")
    return lines


def render_markdown(base: Run, head: Run, result: dict) -> str:
    out: list[str] = ["### UnvibeCode — what this change did", ""]

    workflows = result["workflows"]
    if not base.has_workflow_map or not head.has_workflow_map:
        # Never present an absent baseline as if everything were newly added.
        missing = [
            name for name, run in (("base", base), ("head", head))
            if not run.has_workflow_map
        ]
        out.append(
            "**Business workflows:** not comparable — no workflow map was produced "
            f"for the {' and '.join(missing)} run."
        )
        if head.has_workflow_map:
            out.append("")
            out.append(f"Detected in head ({len(head.workflows)}), baseline unknown:")
            out += [f"- {name}" for name in head.workflows]
    elif workflows["added"] or workflows["removed"]:
        if workflows["added"]:
            out.append(f"**{len(workflows['added'])} new business workflow(s):**")
            out += [f"- {name}" for name in workflows["added"]]
        if workflows["removed"]:
            out.append(f"**{len(workflows['removed'])} workflow(s) no longer detected:**")
            out += [f"- {name}" for name in workflows["removed"]]
    else:
        out.append(f"**Business workflows:** unchanged ({len(head.workflows)}).")
    out.append("")

    rows = [
        ("Files analysed", "files"),
        ("Symbols", "symbols"),
        ("Connections", "connections"),
    ]
    out += ["| | Base | Head | Δ (net) |", "|---|---:|---:|---:|"]
    for title, key in rows:
        before = result["totals"]["base"][key]
        after = result["totals"]["head"][key]
        change = after - before
        out.append(f"| {title} | {before} | {after} | {change:+d} |")
    out.append("")

    for title, key in (("Files added", "files"), ("Symbols added", "symbols")):
        items = result[key]["added"]
        if items:
            out.append(f"**{title} ({len(items)}):**")
            out += _bullets(items)
            out.append("")
    for title, key in (("Files removed", "files"), ("Symbols removed", "symbols")):
        items = result[key]["removed"]
        if items:
            out.append(f"**{title} ({len(items)}):**")
            out += _bullets(items)
            out.append("")

    edges = result["connections"]
    if edges["added"] or edges["removed"]:
        out.append(
            f"**Connections:** {len(edges['added'])} added, "
            f"{len(edges['removed'])} removed."
        )
        for edge in edges["added"][:5]:
            source, relationship, target, symbol = edge
            suffix = f" (`{symbol}`)" if symbol else ""
            out.append(f"- `{source}` --{relationship}--> `{target}`{suffix}")
        out.append("")

    if head.warnings or base.warnings:
        out.append("> **Analysis coverage was incomplete:**")
        for label, run in (("head", head), ("base", base)):
            for warning in run.warnings:
                out.append(f"> - *({label})* {warning}")
        out.append(">")
        out.append(
            "> Treat the comparison above as partial — a deliverable missing from "
            "either run cannot be diffed."
        )
        out.append("")

    out.append(f"<sub>unvibecode-watch · base `{base.label}` → head `{head.label}`</sub>")
    return "\n".join(out)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="unvibecode-watch",
        description="Diff two UnvibeCode runs into a pull-request comment.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    diff_cmd = sub.add_parser("diff", help="Compare a baseline run against a head run")
    diff_cmd.add_argument("baseline")
    diff_cmd.add_argument("head")
    diff_cmd.add_argument("--format", choices=["markdown", "json"], default="markdown")
    diff_cmd.add_argument("--out", help="Write output to this file instead of stdout")
    diff_cmd.add_argument(
        "--fail-on-degraded",
        action="store_true",
        help="Exit 2 if the head run did not produce every deliverable.",
    )

    check_cmd = sub.add_parser("check", help="Report coverage for a single run")
    check_cmd.add_argument("run")

    args = parser.parse_args(argv)

    if args.command == "check":
        run_path = resolve_run(args.run)
        warnings = coverage_warnings(run_path)
        print(f"Run: {run_path}")
        if not warnings:
            print("All components completed.")
            return 0
        for warning in warnings:
            print(f"  ! {warning}")
        return 2

    base = load_run(args.baseline, os.path.basename(resolve_run(args.baseline)))
    head = load_run(args.head, os.path.basename(resolve_run(args.head)))
    result = diff_runs(base, head)

    if args.format == "json":
        rendered = json.dumps(result, indent=2)
    else:
        rendered = render_markdown(base, head, result)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
        print(f"Wrote {args.out}")
    else:
        print(rendered)

    if args.fail_on_degraded and head.warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
