# Stage 3 - Compute metrics and produce the report

## Goal

Compute the requested self-serve metrics from the persisted GitHub and Teams datasets, then write a durable machine-readable result file and a human-readable report.

## Inputs

- `details\github-prs-created.json`
- `details\github-prs-merged.json`
- `details\github-pr-comments.json`
- `details\github-summary.json` when available
- `details\teams-filtered.json`
- `details\teams-enriched.json` when available
- `progress\period.json`

## Outputs

- `result\metrics.json`
- `result\pr-communication-distribution.json`
- `result\pr-communication-bar.png` or a documented fallback such as `result\pr-communication-bar.svg`
- `result\report.md`
- `progress\stage-3.md`

## Checklist

```text
Stage 3 progress
- [ ] Load the persisted GitHub datasets
- [ ] Load the filtered Teams dataset
- [ ] Compute GitHub AutoPR creation and merge counts
- [ ] Compute PR human-communication metrics
- [ ] Compute PR human-communication distribution
- [ ] Compute Teams post and reply metrics
- [ ] Write result\metrics.json
- [ ] Write the PR communication distribution file
- [ ] Generate the PR communication bar graph
- [ ] Write result\report.md
- [ ] Write progress\stage-3.md
```

## Metric definitions

### 1. AutoPRs created in the period

Count the PRs in:

```text
details\github-prs-created.json
```

These counts must exclude draft PRs.
They must also exclude PRs that were closed without merging.

### 2. AutoPRs merged in the period

Count the PRs in:

```text
details\github-prs-merged.json
```

These counts must exclude draft PRs.

### 3. Total filtered AutoPR count

Prefer the filtered count recorded in:

```text
details\github-summary.json
```

Use the `totalFilteredAutoPrCount` label from stage 1 so the report denominator is explicit and traceable.

### 4. PR communication metrics

Use the non-draft PR union from stage 1, typically anchored on non-draft PRs created in the period and excluding PRs that were closed without merging, unless the user asks for another denominator.

For each PR, compute:

```text
humanCommunicationCount =
  issue comments
  + review comments
```

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

### 5. Teams communication metrics

From:

```text
details\teams-filtered.json
```

Compute:
- `relatedPostCount`: number of retained top-level threads
- `averageRepliesPerPost`: arithmetic mean of `replyCount`

Optionally include:
- minimum replies
- maximum replies
- median replies

Prefer the enriched Teams dataset when it helps map retained threads back to specific PRs or libraries. The report should state whether Teams matching used explicit links only or explicit-plus-inferred PR/library matches.

## Workflow

1. Load the persisted period metadata and stage datasets.
2. Compute GitHub created and merged counts.
3. Load or derive the filtered total AutoPR count.
4. Compute per-PR human communication counts from the persisted comment datasets.
5. Compute aggregate PR communication statistics.
6. Compute the PR communication distribution by `humanCommunicationCount`.
7. Generate a bar graph for the distribution, using Python if possible.
8. Compute Teams related-post and reply metrics from the filtered dataset, using enrichment metadata when available.
9. Write `result\metrics.json` first, then generate `result\report.md` from the same numbers.

## PR communication graph

Generate a bar chart where:
- x-axis = human communication count per PR
- y-axis = number of PRs having that count
- the chart visibly shows the filtered total AutoPR count, preferably in the title or subtitle

Preferred implementation:
1. Use Python.
2. Prefer `matplotlib` if it is already available.
3. If `matplotlib` is not available, use Python to generate a simple `.svg` bar chart without installing new packages.

Preferred labeling:
- title: `AutoPR human communication distribution`
- subtitle or secondary title line: `Total filtered AutoPRs: <count>`

Persist:

```text
result\pr-communication-distribution.json
result\pr-communication-bar.png
```

If PNG is not practical in the environment, write:

```text
result\pr-communication-bar.svg
```

and document the fallback in `progress\stage-3.md`.

## Result files

Write a machine-readable result file:

```text
result\metrics.json
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
result\report.md
```

The report should include:
- reporting period
- raw dataset counts
- total filtered AutoPR count
- final metric values
- notable outliers for PR communication
- the PR communication distribution
- the graph file location
- whether Teams matching used explicit links only or inferred PR/library matches
- assumptions and exclusions

Keep the narrative concise and evidence-based. If some source data was incomplete, state that clearly in the report.

## Error handling

- If a required input file is missing, stop and document which prior stage needs to be rerun.
- If counts cannot be reconciled, preserve the partial metrics and describe the inconsistency in `progress\stage-3.md`.
- Do not invent missing PR or Teams data to complete the report.
- If graph generation fails, still persist the distribution JSON and document the failure or fallback in `progress\stage-3.md`.

## Stage notes

Write `progress\stage-3.md` with:
- formulas used
- excluded author rules used
- denominator used for PR communication
- graph generation method and output file
- files read
- any ambiguity or follow-up suggestions
