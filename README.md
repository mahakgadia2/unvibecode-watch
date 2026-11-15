# unvibecode-watch

A working prototype of the Track 2 proposal for the **UnvibeCode Engineering Challenge 2026 (Cohort 3)**.

UnvibeCode answers *"what is this repository?"* — a question a developer asks **once per repository**. That is why first-time usage is strong and repeat usage is weak: after the first run there is no new question for the tool to answer. `unvibecode-watch` turns the same artifacts into an answer to *"what did this change do?"* — a question that recurs on **every pull request**.

It does not re-implement any analysis. It reads the files `unvibecode review` already writes:

| File | Used for |
|---|---|
| `report-support/business-workflows.html` | business workflow names (`h3.workflow-title`) |
| `*repository-context.zip` → `chunks.jsonl` | analysed files, symbols (`qualified_name`, `kind`) |
| `*repository-context.zip` → `connections.jsonl` | connection edges |
| `*repository-context.zip` → `manifest.json` | skipped files |
| `technical-logs/analysis-status.json` | which components actually completed |

Standard library only, matching the UnvibeCode client's own zero-dependency choice. Python 3.11+.

## Usage

```bash
# Diff two runs into a pull-request comment
python unvibecode_watch.py diff BASELINE_RUN HEAD_RUN [--format markdown|json] [--out FILE]

# Report whether a single run actually produced everything it should have
python unvibecode_watch.py check RUN
```

`RUN` is either an analysis folder (`<repo>-unvibecode-analysis-<timestamp>`) or an `unvibecode_results` folder, in which case the most recent analysis is used.

```bash
python -m unvibecode review --repository ./myrepo     # before the change
git checkout my-feature-branch
python -m unvibecode review --repository ./myrepo     # after
python unvibecode_watch.py diff ./old_results ./myrepo/unvibecode_results
```

`.github/workflows/unvibecode-watch.yml` wires this into CI: it reviews the PR base and head, then posts **one sticky comment**, updated in place on each push rather than appended.

See [`SAMPLE_OUTPUT.md`](SAMPLE_OUTPUT.md) — real generated output, not mocked.

## Why a coverage check is part of it

A review can report success while a headline deliverable was never produced. In testing, a run printed `UNVIBECODE REVIEW COMPLETE` and listed three results instead of four, while `technical-logs/analysis-status.json` recorded:

```json
"components": { "business_workflows": "COMPLETED", "risk_findings": "DISABLED" },
"review_outcome": "DISABLED_BY_SERVER_POLICY",
"overall_status": "COMPLETE"
```

A developer cannot distinguish *"we found no risks"* from *"we never looked"* without opening that file. So `check` reads it, and `diff` prints a warning block whenever the head run is incomplete:

```
> **Analysis coverage was incomplete for this run:**
> - `risk findings` was not produced — state `DISABLED` (reason: DISABLED_BY_SERVER_POLICY).
```

`check` exits `2` when any component is incomplete, and `diff --fail-on-degraded` does the same, so CI can gate on it. A tool people return to has to be honest about what it did not do; a confident-looking report that quietly skipped a stage is how trust is lost.

## Verified against

Real runs of UnvibeCode 0.4.0 on four public repositories — `golang-jwt/jwt`, `golang/oauth2`, `go-chi/chi`, `spf13/cobra` — on Windows 11 / CPython 3.15.

As a control, two runs of **the identical commit** (`spf13/cobra` @ `adbc881`) produce an empty diff: 0 added and 0 removed across workflows, files, symbols and connections, confirming the tool reports change only when the analysis actually changed.

## Limitations

Honest scope for a prototype built in one evening:

- **It compares two completed runs.** It does not yet do the incremental, SHA-keyed baseline cache described in the proposal, so each run still re-uploads the whole repository. That caching is step 1 of the implementation plan, not something this prototype claims to have solved.
- **Workflow names are parsed from generated HTML**, since no machine-readable workflow list is published. A JSON summary from UnvibeCode itself (`--format json`) would remove this fragility and is the other half of proposal step 1.
- **Risk findings are not diffed**, because the hosted preview returned `risk_findings: DISABLED` on every run tested, so there was no data to compare. The code path for reporting its absence exists and is exercised.
- **UnvibeCode uploads source to a hosted service**, so running it in CI sends repository contents off the runner. Teams should confirm that is acceptable before enabling the workflow.
- Symbol identity is `file::qualified_name`, so a symbol moved between files reads as one removal plus one addition rather than a move.
