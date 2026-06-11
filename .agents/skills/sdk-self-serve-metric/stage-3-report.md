# Stage 3 - Compute metrics and produce the report

## Goal

Compute the requested self-serve metrics from the persisted GitHub and Teams datasets for each language entry, then write durable per-language result files and reports.

## Inputs

- `sdk-source.md`
- `details\<language-key>\github-prs-created.json`
- `details\<language-key>\github-prs-merged.json`
- `details\<language-key>\github-pr-comments.json`
- `details\<language-key>\github-summary.json` when available
- `details\<language-key>\teams-filtered.json`
- `details\<language-key>\teams-enriched.json` when available
- `progress\period.json`

## Outputs

- `result\<language-key>\metrics.json`
- `result\<language-key>\pr-communication-distribution.json`
- `result\<language-key>\pr-communication-bar.png` or a documented fallback such as `result\<language-key>\pr-communication-bar.svg`
- `result\<language-key>\report.md`
- `result\language-summary-metrics.json`
- `result\language-pr-count-and-average-human-communication-bar.png` or a documented fallback such as `result\language-pr-count-and-average-human-communication-bar.svg`
- `result\language-teams-post-count-bar.png` or a documented fallback such as `result\language-teams-post-count-bar.svg`
- `progress\stage-3.md`

## Checklist

```text
Stage 3 progress
- [ ] Load language entries from sdk-source.md
- [ ] Load the persisted GitHub datasets for each language
- [ ] Load the filtered Teams dataset for each language
- [ ] Compute GitHub AutoPR creation and merge counts for each language
- [ ] Compute PR human-communication metrics for each language
- [ ] Compute PR human-communication distribution for each language
- [ ] Compute Teams post and reply metrics for each language
- [ ] Write result files per language
- [ ] Generate the PR communication bar graph per language
- [ ] Generate cross-language summary bar graphs
- [ ] Write report.md per language
- [ ] Write progress\stage-3.md
```

## Metric definitions

### 1. AutoPRs created in the period

For the current language entry, count the PRs in:

```text
details\<language-key>\github-prs-created.json
```

These counts must exclude draft PRs.
They must also exclude PRs that were closed without merging.

### 2. Created-period AutoPRs that were merged

Count the PRs in:

```text
details\<language-key>\github-prs-merged.json
```

These counts must be a subset of `details\<language-key>\github-prs-created.json`.

### 3. Created-period AutoPRs that are currently open

Count the PRs in:

```text
details\<language-key>\github-prs-open.json
```

These counts must be a subset of `details\<language-key>\github-prs-created.json`.

### 4. Total filtered AutoPR count

Prefer the filtered count recorded in:

```text
details\<language-key>\github-summary.json
```

Use the `totalFilteredAutoPrCount` label from stage 1 so the report denominator is explicit and traceable.
This should match the filtered created-period cohort.

### 5. PR communication metrics

Use the non-draft created-period cohort from stage 1 for the current language, excluding PRs that were closed without merging, unless the user asks for another denominator.

For each PR, compute:

```text
humanCommunicationCount =
  issue comments
  + review comments
```

Do not include review submission events such as `APPROVED`, `CHANGES_REQUESTED`, or review-summary `COMMENTED` entries in `humanCommunicationCount`.

Exclude comments authored by:
- `Copilot`
- `copilot-pull-request-reviewer`
- accounts ending in `[bot]`
- `azure-sdk`
- `app/azure-sdk-automation`

Then compute:
- minimum `humanCommunicationCount`
- maximum `humanCommunicationCount`
- average `humanCommunicationCount`

Persist per-PR counts as part of the result payload so the aggregate can be audited later.

For transparency, also persist the excluded-comment breakdown per PR if that helps explain the final counts.

Also compute a distribution of communication counts, for example:

```json
[
  { "commentCount": 0, "prCount": 10 },
  { "commentCount": 1, "prCount": 10 },
  { "commentCount": 2, "prCount": 3 }
]
```

This distribution should drive the bar graph.

### 6. Teams communication metrics

From:

```text
details\<language-key>\teams-filtered.json
```

Compute:
- `relatedPostCount`: number of retained top-level threads
- `averageRepliesPerPost`: arithmetic mean of `replyCount`

Optionally include:
- minimum replies
- maximum replies
- median replies

Prefer the enriched Teams dataset when it helps map retained threads back to specific PRs or libraries. The report should state whether Teams matching used explicit links only or explicit-plus-inferred PR/library matches for that language.

Retained Teams threads may include both SDK-repo AutoPR discussions and language-channel SDK validation or generation-failure triage linked to `Azure/azure-rest-api-specs` PRs. The report should make that scope clear when such threads are present.

## Workflow

1. Load the persisted period metadata and the language entries from `sdk-source.md`.
2. For each language, load the stage datasets.
3. Compute the created-period cohort count and its merged/currently-open subsets.
4. Load or derive the filtered total AutoPR count.
5. Compute per-PR human communication counts from the persisted comment datasets.
6. Compute aggregate PR communication statistics.
7. Compute the PR communication distribution by `humanCommunicationCount`.
8. Generate a bar graph for the distribution, using Python if possible.
9. Compute Teams related-post and reply metrics from the filtered dataset, using enrichment metadata when available.
10. Write `result\<language-key>\metrics.json` first, then generate `result\<language-key>\report.md` from the same numbers.
11. Build a cross-language summary dataset from the per-language metrics.
12. Generate a combined cross-language bar chart for AutoPR count and average human communication per PR, plus a separate retained Teams post count chart.

## PR communication graph

Generate a bar chart where:
- x-axis = human communication count per PR
- y-axis = number of PRs having that count
- the chart visibly shows the filtered total AutoPR count, preferably in the title or subtitle
- the chart visibly shows the average human communication count, preferably in the title or subtitle

Preferred implementation:
1. Use Python.
2. Prefer `matplotlib` if it is already available.
3. If `matplotlib` is not available, use Python to generate a simple `.svg` bar chart without installing new packages.

Preferred labeling:
- title: `AutoPR human communication distribution`
- subtitle or secondary title line: `Total filtered AutoPRs: <count>`
- subtitle or secondary title line: `Average human communication count: <avg>`

Persist:

```text
result\<language-key>\pr-communication-distribution.json
result\<language-key>\pr-communication-bar.png
```

If PNG is not practical in the environment, write:

```text
result\<language-key>\pr-communication-bar.svg
```

and document the fallback in `progress\stage-3.md`.

## Cross-language summary graphs

After the per-language metrics are computed, generate a summary dataset and three additional bar charts across all languages in `sdk-source.md`.

Persist the summary dataset to:

```text
result\language-summary-metrics.json
```

Suggested shape:

```json
[
  {
    "languageKey": "java",
    "language": "Java",
    "createdCount": 21,
    "averageHumanCommunication": 1.71,
    "teamsRelatedPostCount": 2
  }
]
```

Generate these charts:

1. `result\language-pr-count-and-average-human-communication-bar.png`
   - x-axis = language
   - visually combine:
     - filtered AutoPR count in the created-period cohort
     - average human communication count per PR
   - you may use grouped bars, dual axes, or another clear layout that keeps both measures readable in one graph
2. `result\language-teams-post-count-bar.png`
   - x-axis = language
   - y-axis = retained Teams post count

If PNG is not practical, write `.svg` fallbacks with the same file stems and document the fallback in `progress\stage-3.md`.

## Result files

Write a machine-readable result file:

```text
result\<language-key>\metrics.json
```

Suggested shape:

```json
{
  "period": {
    "start": "2026-05-01",
    "end": "2026-05-31",
    "key": "202605"
  },
  "github": {
    "createdCount": 0,
    "mergedCount": 0,
    "totalFilteredAutoPrCount": 0,
    "humanCommunication": {
      "min": 0,
      "max": 0,
      "average": 0.0,
      "distribution": [],
      "perPr": []
    }
  },
  "teams": {
    "relatedPostCount": 0,
    "averageRepliesPerPost": 0.0
  }
}
```

Write a human-readable summary to:

```text
result\<language-key>\report.md
```

Each per-language report should include:
- reporting period
- language name and source entry used
- raw dataset counts
- total filtered AutoPR count
- a clear statement that the GitHub reporting ensemble is the filtered AutoPRs created in the period
- final metric values
- notable outliers for PR communication
- the PR communication distribution
- the graph file location
- whether Teams matching used explicit links only or inferred PR/library matches
- whether retained Teams threads include `Azure/azure-rest-api-specs` validation-failure discussions
- assumptions and exclusions

Keep the narrative concise and evidence-based. If some source data was incomplete, state that clearly in the report.

## Error handling

- If a required input file is missing, stop and document which prior stage needs to be rerun.
- If counts cannot be reconciled, preserve the partial metrics and describe the inconsistency in `progress\stage-3.md`.
- Do not invent missing PR or Teams data to complete the report.
- If graph generation fails, still persist the distribution JSON and document the failure or fallback in `progress\stage-3.md`.
- If one language fails while others succeed, preserve the successful per-language outputs and document the blocked language separately.

## Stage notes

Write `progress\stage-3.md` with:
- language entries processed
- formulas used
- excluded author rules used
- denominator used for PR communication per language
- graph generation method and output file per language
- cross-language summary graph generation method and output files
- files read per language
- any ambiguity or follow-up suggestions
