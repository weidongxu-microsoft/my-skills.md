---
name: sdk-self-serve-metric
description: '**WORKFLOW SKILL** - Collects staged self-serve metrics for Azure Java AutoPRs and related Teams discussions, persisting raw data, filtered thread data, progress notes, and final reports under self-serve-metric-<yyyymm>. USE FOR: "create sdk self serve metric for 202605", "collect Java AutoPR self-serve metrics for May 2026".'
---

# SDK Self-Serve Metric

Use this skill when the user wants a staged metric/report for Azure Java management-plane AutoPRs and the related Teams discussion in the Java channel.

## Purpose

Collect, persist, filter, and report self-serve operational metrics for Java management-plane AutoPRs and the related Teams communication for a requested reporting period.

## Scope

This skill is for:
- GitHub repository: `Azure/azure-sdk-for-java`
- PR title pattern: `[AutoPR azure-resourcemanager-`
- Teams channel: `Language - Java`
- Reporting period: a closed calendar range such as `2026-05-01` through `2026-05-31`
- non-draft PRs only
- PRs that are still open or merged; exclude PRs that were closed without merging

This skill is not for:
- Non-Java repositories
- Non-management-plane PRs
- Ad-hoc PR review or merge workflows
- One-off Teams lookups without the staged metric/report output

## Inputs

Required inputs:
- reporting period, preferably as a closed date range such as `2026-05-01` through `2026-05-31`

Optional inputs:
- explicit output folder key if the user wants something other than the default `yyyymm`
- whether to rerun only a later stage using persisted files from a previous run

If the reporting period is missing or ambiguous, stop and ask the user before creating files.

## Outputs

Successful completion produces:
- a folder `self-serve-metric-<yyyymm>` in the repository root
- persisted stage artifacts under `details\`, `progress\`, and `result\`
- a filtered GitHub collection summary that includes the total AutoPR count in scope
- a machine-readable metrics file
- a human-readable report
- a bar graph for AutoPR communication distribution with the filtered total AutoPR count and average communication count shown on the chart

## Success criteria

The skill is complete only when:
- all requested stage outputs are written to disk
- raw source data needed by later stages is preserved
- filtered Teams threads can be traced back to raw source records
- the final report includes the requested GitHub and Teams metrics

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
- `details\`: raw and normalized data files used by later stages
- `progress\`: stage notes, checklists, open questions, and assumptions
- `result\`: final metrics and human-readable report

## Staged workflow

Run the work in these stages and persist outputs after each one:

1. [Stage 1 - Collect all source data](./stage-1-collect.md)
2. [Stage 2 - Filter Teams threads to the relevant management-plane discussions](./stage-2-filter-teams.md)
3. [Stage 3 - Compute metrics and produce the report](./stage-3-report.md)

Do not skip persistence between stages. The goal is that stage 2 and stage 3 can be rerun without recollecting everything.

If the user asks to stop after a stage, still persist that stage's outputs and clearly record what remains for the next stage.

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

The final report must cover at least these metrics for the requested period:

1. Count of AutoPRs created in the period
2. Count of those AutoPRs that were merged
3. Count of those AutoPRs that are currently open
4. PR communication metrics for AutoPRs in scope, excluding bot and Copilot comments:
   - minimum
   - maximum
   - average
   - distribution by comment count, for example `0 -> 10 PRs`, `1 -> 10 PRs`, `2 -> 3 PRs`
5. Teams metrics for threads related to `azure-resourcemanager-*`:
   - count of related top-level posts
   - average replies per related post

Unless the user asks for different denominators, the reporting ensemble is the filtered set of AutoPRs created in the period. All other GitHub counts should be subsets of that ensemble.

## Data to collect

Stage 1 must collect enough raw data to support all later calculations. Do not collect only the final aggregates.

### GitHub data

Collect all of the following PR datasets:

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

### Teams data

Collect all top-level posts and replies from the Java Teams channel during the period, before any filtering.

If the Microsoft 365 / Work IQ tool requires EULA acceptance or additional sign-in, stop and ask the user instead of fabricating data.

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
  - `Java-<number>` generation identifiers
  - `azure-resourcemanager-*` library names
  - phrases like `Java sdk review for <library or service>`

If the Teams tool returns shortened or paraphrased text, run a second enrichment pass to recover the concrete PR reference from the thread text and the GitHub AutoPR dataset collected in stage 1.

## Communication rules for PR metrics

For PR communication metrics, exclude comments authored by:
- `Copilot`
- `copilot-pull-request-reviewer`
- accounts ending in `[bot]`
- `azure-sdk`
- `app/azure-sdk-automation`

Persist the raw comments first, then derive the filtered human-only counts in stage 3.

When in doubt, keep the raw comment and classify the exclusion in derived output instead of deleting data from the raw record.

## Communication rules for Teams metrics

For Teams, collect all posts and replies first. Do not discard bot-authored content during stage 1.

During stage 2, mark whether each thread is related to `azure-resourcemanager-*`. Preserve enough metadata so stage 3 can compute either all-reply counts or human-only counts later if needed.

If a Teams thread cannot be confidently matched, keep it out of the filtered dataset and record the ambiguity in `progress\stage-2.md`.

When a thread does not contain an explicit PR URL, it can still be in scope if the post text or reply text can be matched to an AutoPR title, `Java-<number>` release identifier, or inferred `azure-resourcemanager-*` library.

## Preferred tools

- Use `gh` CLI for GitHub collection.
- Use Microsoft 365 Copilot / Work IQ tooling for the Teams channel collection.
- Persist raw responses to files before deriving filtered or summarized datasets.

## Error handling

- If GitHub search results appear incomplete, narrow the collection window and persist the partial results before retrying.
- If Teams access requires consent or sign-in, stop and ask the user instead of guessing.
- If a stage cannot finish, write the partial artifacts that were successfully collected and document the blocker in the corresponding `progress\stage-<n>.md`.
- Do not overwrite previously collected raw files without a clear reason; prefer replacing them only when rerunning the same stage intentionally.

## Minimum artifact set

By the end of the full workflow, the folder should contain at least:

```text
details\github-prs-created.json
details\github-prs-merged.json
details\github-prs-open.json
details\github-pr-comments.json
details\teams-raw.json
details\teams-filtered.json
progress\period.json
progress\stage-1.md
progress\stage-2.md
progress\stage-3.md
result\metrics.json
details\github-summary.json
result\pr-communication-distribution.json
result\pr-communication-bar.png
result\report.md
```

If you need additional files, add them under the same folder tree and keep the names self-explanatory.
