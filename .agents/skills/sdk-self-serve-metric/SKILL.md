---
name: sdk-self-serve-metric
description: '**WORKFLOW SKILL** - Collects staged self-serve metrics for Azure SDK AutoPRs and related Teams discussions across languages listed in sdk-source.md, persisting raw data, filtered thread data, progress notes, and per-language reports under self-serve-metric-<yyyymm>. USE FOR: "create sdk self serve metric for 202605", "collect SDK self-serve metrics for May 2026".'
---

# SDK Self-Serve Metric

Use this skill when the user wants a staged metric/report for Azure SDK AutoPRs and the related Teams discussion, with the language sources driven by `sdk-source.md`.

## Purpose

Collect, persist, filter, and report self-serve operational metrics for SDK AutoPRs and the related Teams communication for a requested reporting period, producing the same outputs per language.

## Scope

This skill is for:
- SDK languages listed in `./sdk-source.md`
- one GitHub repository / AutoPR pattern / library pattern / Teams channel tuple per language source entry
- reporting periods such as `2026-05-01` through `2026-05-31`
- non-draft PRs only
- PRs that are still open or merged; exclude PRs that were closed without merging

This skill is not for:
- repositories or languages not listed in `sdk-source.md`
- Ad-hoc PR review or merge workflows
- One-off Teams lookups without the staged metric/report output

## Language source catalog

Treat `./sdk-source.md` as the source of truth for which languages to process.

Each top-level heading represents one language entry. For each entry, read at least:
- GitHub repository
- PR title pattern
- Lib name pattern
- Teams channel
- Teams link

The workflow should iterate the language entries found in `sdk-source.md` rather than hardcoding Java, .NET, Python, TypeScript, Go, or any future language explicitly in the instructions.

When a new language is added to `sdk-source.md` with the same fields, the skill should process it automatically.

## Inputs

Required inputs:
- reporting period, preferably as a closed date range such as `2026-05-01` through `2026-05-31`
- `sdk-source.md`

Optional inputs:
- explicit output folder key if the user wants something other than the default `yyyymm`
- whether to rerun only a later stage using persisted files from a previous run

If the reporting period is missing or ambiguous, stop and ask the user before creating files.

## Outputs

Successful completion produces:
- a folder `self-serve-metric-<yyyymm>` in the repository root
- persisted stage artifacts under `details\`, `progress\`, and `result\`
- one per-language filtered GitHub collection summary
- one machine-readable metrics file per language
- one human-readable report per language
- one bar graph per language for AutoPR communication distribution with the filtered total AutoPR count and average communication count shown on the chart
- cross-language summary bar charts for:
  - AutoPR count and average human communication per PR by language in one combined graph
  - SDK generation related Teams post count by language
- an optional PowerPoint deck when the user explicitly asks for one

## Success criteria

The skill is complete only when:
- all requested stage outputs are written to disk
- raw source data needed by later stages is preserved
- filtered Teams threads can be traced back to raw source records
- each language listed in `sdk-source.md` has the requested GitHub and Teams metrics, or an explicit documented blocker

## Output folder

Create a report workspace folder in the current repository root:

```text
<repo-root>\self-serve-metric-<yyyymm>\
```

Example:

```text
self-serve-metric-202605\
```

Create and keep all stage artifacts in these subfolders:

```text
self-serve-metric-<yyyymm>\
  details\
  progress\
  result\
```

Expected usage of each folder:
- `details\`: raw and normalized data files used by later stages, typically grouped per language
- `progress\`: stage notes, checklists, open questions, and assumptions
- `result\`: final metrics and human-readable reports, typically grouped per language

Recommended per-language layout:

```text
self-serve-metric-<yyyymm>\
  details\
    <language-key>\
      github-prs-created.json
      github-prs-merged.json
      github-prs-open.json
      github-pr-comments.json
      github-pr-union.json
      github-summary.json
      teams-raw.json
      teams-enriched.json
      teams-filtered.json
  result\
    language-summary-metrics.json
    language-pr-count-and-average-human-communication-bar.png
    language-teams-post-count-bar.png
    self-serve-sdk-generation-review-metrics-<yyyymm>.pptx
    <language-key>\
      metrics.json
      pr-communication-distribution.json
      pr-communication-bar.png
      report.md
```

Derive `<language-key>` from the language heading in `sdk-source.md`, normalized to a stable lowercase kebab-case form.

## Staged workflow

Run the work in these stages and persist outputs after each one:

1. [Stage 1 - Collect all source data](./stage-1-collect.md)
2. [Stage 2 - Filter Teams threads to the relevant management-plane discussions](./stage-2-filter-teams.md)
3. [Stage 3 - Compute metrics and produce the report](./stage-3-report.md)
5. [Stage 5 - Create presentation deck](./stage-5-create-ppt.md) — only when the user explicitly asks for a PPT or PowerPoint

Do not skip persistence between stages. The goal is that stage 2 and stage 3 can be rerun without recollecting everything, and stage 5 can be rerun without recomputing the metrics.

If the user asks to stop after a stage, still persist that stage's outputs and clearly record what remains for the next stage.

Stage 4 is intentionally reserved for future required analysis work and is not part of the current skill behavior.

Stage 5 is optional. Do not create a PowerPoint deck unless the user explicitly asks for it.

## Period handling

At the start of the workflow, normalize the requested period into:
- `periodStart`: inclusive date, for example `2026-05-01`
- `periodEnd`: inclusive date, for example `2026-05-31`
- `periodKey`: `yyyymm`, for example `202605`

Persist these values in:

```text
progress\period.json
```

Also record the original user wording for the period in `progress\stage-1.md` so later reruns preserve the original reporting intent.

## Metrics to produce

Each per-language report must cover at least these metrics for the requested period:

1. Count of AutoPRs created in the period
2. Count of those AutoPRs that were merged
3. Count of those AutoPRs that are currently open
4. PR human comment metrics for AutoPRs in scope, counting only issue comments and review comments from non-bot authors:
   - minimum
   - maximum
   - average
   - distribution by comment count, for example `0 -> 10 PRs`, `1 -> 10 PRs`, `2 -> 3 PRs`
5. Teams metrics for retained language-channel threads, including both AutoPR discussions and SDK validation / generation-failure discussions tied to `Azure/azure-rest-api-specs` PRs for that language:
   - count of related top-level posts
   - average replies per related post

Unless the user asks for different denominators, the reporting ensemble for each language is the filtered set of AutoPRs created in the period for that language entry. All other GitHub counts should be subsets of that ensemble.

## Data to collect

Stage 1 must collect enough raw data to support all later calculations. Do not collect only the final aggregates.

### GitHub data

For each language entry from `sdk-source.md`, collect all of the following PR datasets:

1. Non-draft AutoPRs created within the period, excluding PRs that were later closed without merging
2. The subset of dataset 1 that was merged
3. The subset of dataset 1 that is currently open and not merged

For each PR collected, persist enough detail to support stage 3:
- PR number
- title
- URL
- author login
- created time
- merged time
- closed time
- state
- draft flag
- mergeability / review status if available
- PR body
- all issue comments
- all review comments or review-thread comments
- optional review submissions if you want audit context, but keep them separate from the comment-count dataset

### Teams data

Collect all top-level posts and replies from the language entry's Teams channel during the period, before any filtering. Prefer the `workiq` MCP server (Microsoft Graph) with the two-phase enumerate-then-fetch pattern in [stage 1](./stage-1-collect.md); use Microsoft 365 Copilot / Work IQ grounding only as a fallback.

If the Microsoft 365 / Work IQ tool requires EULA acceptance or additional sign-in, stop and ask the user instead of fabricating data.

`workiq`/Graph caps each collection (and each reply page) at 10 items and rejects pagination, so coverage is the top-10 most-recently-active threads per channel. Run the metric soon after the period ends, and flag any thread or reply page that hits the 10-item cap as a lower bound.

If the raw Teams output is too large for a single collection request, collect it in smaller time windows and merge the normalized results into a single persisted dataset.

Teams collection must preserve the original post content as faithfully as possible. Do not rely on summaries or shortened paraphrases when the purpose is matching a thread to a specific SDK PR or library.

For each Teams thread, try to persist:
- full original top-level post body
- normalized top-level post body
- full original reply bodies
- normalized reply bodies
- any explicit PR links
- any inferred PR references such as:
  - AutoPR title fragments
  - generation identifiers such as `Java-<number>`, `.NET-<number>`, `Python-<number>`, `JS-<number>`, `Go-<number>`
  - language-entry library names from `sdk-source.md`
  - `Azure/azure-rest-api-specs` PR links tied to SDK validation or generation failures for the language entry
  - phrases like `<language> sdk review for <library or service>`
  - phrases like `SDK Validation - <language>`, `SDK generation failing`, or similar validation-failure wording

If the Teams tool returns shortened or paraphrased text, run a second enrichment pass to recover the concrete PR reference from the thread text and the GitHub AutoPR dataset collected in stage 1.

## Communication rules for PR metrics

For PR communication metrics, count only:
- issue comments
- review comments or review-thread comments

Do not count review submission events such as `APPROVED`, `CHANGES_REQUESTED`, or review-summary `COMMENTED` entries in the human comment count, even when authored by humans.

Exclude comments authored by:
- `Copilot`
- `copilot-pull-request-reviewer`
- accounts ending in `[bot]`
- `azure-sdk`
- `app/azure-sdk-automation`

Persist the raw comments first, then derive the filtered human-only counts in stage 3.

When in doubt, keep the raw comment and classify the exclusion in derived output instead of deleting data from the raw record.

## Communication rules for Teams metrics

For Teams, collect all posts and replies first. Do not discard bot-authored content during stage 1.

During stage 2, mark whether each thread is related to the current language entry. This includes both in-scope AutoPR discussion threads and language-channel triage threads about SDK validation or generation failures linked to `Azure/azure-rest-api-specs` PRs. Preserve enough metadata so stage 3 can compute either all-reply counts or human-only counts later if needed.

If a Teams thread cannot be confidently matched, keep it out of the filtered dataset and record the ambiguity in `progress\stage-2.md`.

When a thread does not contain an explicit PR URL, it can still be in scope if the post text or reply text can be matched to an AutoPR title, a generation identifier, or an inferred library from the current language entry.

## Preferred tools

- Use `gh` CLI for GitHub collection.
- For the Teams channel collection, prefer the `workiq` MCP server (a direct Microsoft Graph gateway)
  using the two-phase enumerate-then-fetch pattern described in stage 1. Fall back to Microsoft 365
  Copilot / Work IQ grounding only when `workiq` Graph access is unavailable; that grounding search
  is unreliable (empty results, "expired records", or timeouts) and its timeout is not
  CLI-configurable because the server is host-injected.
- Persist raw responses to files before deriving filtered or summarized datasets.

## Error handling

- If GitHub search results appear incomplete, narrow the collection window and persist the partial results before retrying.
- If Teams access requires consent or sign-in, stop and ask the user instead of guessing.
- If a stage cannot finish, write the partial artifacts that were successfully collected and document the blocker in the corresponding `progress\stage-<n>.md`.
- Do not overwrite previously collected raw files without a clear reason; prefer replacing them only when rerunning the same stage intentionally.

## Minimum artifact set

By the end of the full workflow, the folder should contain at least:

```text
details\<language-key>\github-prs-created.json
details\<language-key>\github-prs-merged.json
details\<language-key>\github-prs-open.json
details\<language-key>\github-pr-comments.json
details\<language-key>\teams-raw.json
details\<language-key>\teams-filtered.json
progress\period.json
progress\stage-1.md
progress\stage-2.md
progress\stage-3.md
result\<language-key>\metrics.json
details\<language-key>\github-summary.json
result\<language-key>\pr-communication-distribution.json
result\<language-key>\pr-communication-bar.png
result\<language-key>\report.md
result\language-summary-metrics.json
result\language-pr-count-and-average-human-communication-bar.png
result\language-teams-post-count-bar.png
```

If the user explicitly asks for a presentation deck, also produce:

```text
result\self-serve-sdk-generation-review-metrics-<yyyymm>.pptx
```

Apply this minimum artifact set per language under the per-language folder layout, plus the cross-language summary artifacts at the `result\` root. If you need additional files, add them under the same folder tree and keep the names self-explanatory.
