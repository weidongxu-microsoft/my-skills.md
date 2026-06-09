# Stage 3 - Compute metrics and produce the report

## Goal

Compute the requested self-serve metrics from the persisted GitHub and Teams datasets, then write a durable machine-readable result file and a human-readable report.

## Inputs

- `details\github-prs-created.json`
- `details\github-prs-merged.json`
- `details\github-pr-comments.json`
- `details\teams-filtered.json`
- `details\teams-enriched.json` when available
- `progress\period.json`

## Outputs

- `result\metrics.json`
- `result\report.md`
- `progress\stage-3.md`

## Checklist

```text
Stage 3 progress
- [ ] Load the persisted GitHub datasets
- [ ] Load the filtered Teams dataset
- [ ] Compute GitHub AutoPR creation and merge counts
- [ ] Compute PR human-communication metrics
- [ ] Compute Teams post and reply metrics
- [ ] Write result\metrics.json
- [ ] Write result\report.md
- [ ] Write progress\stage-3.md
```

## Metric definitions

### 1. AutoPRs created in the period

Count the PRs in:

```text
details\github-prs-created.json
```

### 2. AutoPRs merged in the period

Count the PRs in:

```text
details\github-prs-merged.json
```

### 3. PR communication metrics

Use the PR union from stage 1, typically anchored on PRs created in the period unless the user asks for another denominator.

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

### 4. Teams communication metrics

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
3. Compute per-PR human communication counts from the persisted comment datasets.
4. Compute aggregate PR communication statistics.
5. Compute Teams related-post and reply metrics from the filtered dataset, using enrichment metadata when available.
6. Write `result\metrics.json` first, then generate `result\report.md` from the same numbers.

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
    "humanCommunication": {
      "min": 0,
      "max": 0,
      "average": 0.0,
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
- final metric values
- notable outliers for PR communication
- whether Teams matching used explicit links only or inferred PR/library matches
- assumptions and exclusions

Keep the narrative concise and evidence-based. If some source data was incomplete, state that clearly in the report.

## Error handling

- If a required input file is missing, stop and document which prior stage needs to be rerun.
- If counts cannot be reconciled, preserve the partial metrics and describe the inconsistency in `progress\stage-3.md`.
- Do not invent missing PR or Teams data to complete the report.

## Stage notes

Write `progress\stage-3.md` with:
- formulas used
- excluded author rules used
- denominator used for PR communication
- files read
- any ambiguity or follow-up suggestions
