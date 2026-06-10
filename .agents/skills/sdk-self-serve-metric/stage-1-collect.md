# Stage 1 - Collect all source data

## Goal

Collect and persist all GitHub and Teams source data needed by later stages. This stage is about durable raw data capture, not final filtering or reporting.

## Inputs

- `periodStart`
- `periodEnd`
- `periodKey`
- repository root path

## Outputs

- output folders under `self-serve-metric-<yyyymm>\`
- raw and normalized GitHub datasets
- a filtered GitHub collection summary with total counts
- raw and normalized Teams datasets
- enriched Teams datasets with inferred PR and library references when possible
- `progress\stage-1.md`

## Checklist

```text
Stage 1 progress
- [ ] Normalize the requested period and create the output folders
- [ ] Collect AutoPRs created within the period
- [ ] Collect AutoPRs merged within the period
- [ ] Collect open ready-for-review AutoPRs created within the period
- [ ] Collect comments for the GitHub PRs in scope
- [ ] Collect all posts and replies from the Java Teams channel during the period
- [ ] Persist raw and normalized files in details\
- [ ] Write stage notes to progress\stage-1.md
```

## Folder setup

Create these folders first:

```text
self-serve-metric-<yyyymm>\
self-serve-metric-<yyyymm>\details\
self-serve-metric-<yyyymm>\progress\
self-serve-metric-<yyyymm>\result\
```

Write the normalized period metadata to:

```text
progress\period.json
```

## Workflow

1. Normalize the requested reporting period and create the output folders.
2. Collect the GitHub created-period AutoPR cohort.
3. Apply the GitHub filters that exclude draft PRs and PRs closed without merging.
4. Derive the merged and open ready-for-review subsets from that created-period cohort.
5. Compute and persist a filtered GitHub summary, including the total AutoPR count in scope.
6. Build the union of in-scope PR numbers and collect PR bodies plus comment data.
7. Collect the raw Teams channel threads and replies for the same period.
8. Enrich Teams threads with explicit or inferred PR references using the GitHub AutoPR dataset.
9. Persist raw outputs before creating normalized JSON files.
10. Write stage notes describing data coverage, blockers, and file locations.

## GitHub collection

### Dataset A - AutoPRs created within the period

Search for PRs where:
- title contains `[AutoPR azure-resourcemanager-`
- PR is not draft
- `createdAt` is within the requested period
- exclude PRs that are closed without being merged

Example search:

```bash
gh pr list --state all \
  --search "\"[AutoPR azure-resourcemanager-\" draft:false created:2026-05-01..2026-05-31" \
  --json number,title,url,author,createdAt,mergedAt,closedAt,state,isDraft,headRefOid \
  --repo Azure/azure-sdk-for-java
```

Then normalize the result by removing any PR where:
- `isDraft == true`, or
- `state == "CLOSED"` and `mergedAt` is empty

Persist to:

```text
details\github-prs-created.json
```

### Dataset B - Created-period AutoPRs that were merged

Build this dataset from dataset A only.

Keep PRs where:
- `mergedAt` is present

Persist to:

```text
details\github-prs-merged.json
```

### Dataset C - Open ready-for-review AutoPRs created within the period

Build this dataset from dataset A only.

Keep PRs where:
- `state == "OPEN"`
- `mergedAt` is empty
- review is still required / ready for review

If review-state fields such as `mergeStateStatus` or `reviewDecision` are not already available from dataset A, enrich the created-period cohort before deriving this subset.

Persist to:

```text
details\github-prs-open-ready.json
```

### Dataset D - PR body and comments

Because datasets B and C are subsets of dataset A, the union should normally equal dataset A. For every PR in that union, collect:
- PR body
- issue comments
- review comments or review-thread comments

Prefer a single normalized file keyed by PR number. The normalized record should include:

```json
{
  "number": 12345,
  "url": "https://github.com/Azure/azure-sdk-for-java/pull/12345",
  "body": "...",
  "issueComments": [],
  "reviewComments": []
}
```

Useful commands:

```bash
gh pr view <PR_NUMBER> --json body,author,createdAt,mergedAt,closedAt,state,isDraft,title,url --repo Azure/azure-sdk-for-java

gh api repos/Azure/azure-sdk-for-java/issues/<PR_NUMBER>/comments

gh api repos/Azure/azure-sdk-for-java/pulls/<PR_NUMBER>/comments
```

If you need author metadata or threaded review context, use `gh api graphql`.

Persist to:

```text
details\github-pr-comments.json
```

For reproducibility, also persist the union PR number list to:

```text
details\github-pr-union.json
```

Also persist a filtered GitHub summary file that includes the total count label for in-scope AutoPRs:

```text
details\github-summary.json
```

Suggested shape:

```json
{
  "createdCount": 21,
  "mergedCount": 19,
  "openReadyCount": 1,
  "unionCount": 21,
  "totalFilteredAutoPrCount": 21,
  "filters": {
    "excludeDraft": true,
    "excludeClosedUnmerged": true
  }
}
```

`totalFilteredAutoPrCount` should be computed after the draft and closed-unmerged filters are applied. Unless the user requests a different denominator, this is the created-period reporting ensemble, and `mergedCount` plus `openReadyCount` must be interpretable as subsets of that same cohort.

## Teams collection

Collect all top-level posts and replies from the Java Teams channel during the requested period before any filtering.

Channel URL:

```text
https://teams.microsoft.com/l/channel/19%3A5e673e41085f4a7eaaf20823b85b2b53%40thread.skype/Language%20-%20Java?groupId=3e17dcb0-4257-4a30-b843-77f47f1d4121&tenantId=72f988bf-86f1-41af-91ab-2d7cd011db47
```

Use Microsoft 365 Copilot / Work IQ to request structured output. Ask for:
- thread identifier
- top-level post author
- top-level post timestamp
- full original top-level post body
- normalized top-level post body if the tool returns both
- reply count
- replies array with author, timestamp, full original body, and normalized body if available
- explicit links present in the post or replies

Ask the tool to avoid summarizing, shortening, or paraphrasing the post body. The goal is to capture the original wording, because abbreviated text can hide the PR title or library name needed for matching.

Prefer a prompt like:

```text
From the Teams channel at <channel-url>, list all top-level posts and all replies created between <periodStart> and <periodEnd>. Return structured JSON only. Preserve the full original text of each post and reply; do not summarize or paraphrase. For each thread include threadId, postAuthor, postTime, originalPostBody, normalizedPostBody if available, replyCount, replies[{author,time,originalBody,normalizedBody}], and any explicit links found in the post or replies.
```

Persist:
- the raw tool response to `details\teams-raw-response.txt`
- the normalized thread list to `details\teams-raw.json`

If the tool cannot return strict JSON, save the raw response first and then create a normalized JSON file beside it.

If the channel data is too large for one request:
1. split the period into smaller windows
2. collect each window separately
3. persist the per-window raw files in `details\teams-raw-parts\`
4. merge them into `details\teams-raw.json`

## Teams enrichment

After collecting the raw Teams threads, enrich them before stage 2 filtering.

For each thread, try to derive:
- `explicitPrLinks`
- `linkedPrNumbers`
- `linkedPrTitles`
- `linkedLibraries`
- `matchEvidence`

Use these strategies in order:

1. Extract explicit GitHub PR links from the post body and replies.
2. Match exact AutoPR title fragments such as:
   - `[AutoPR azure-resourcemanager-foo]-generated-from-SDK Generation - Java-1234567`
3. Match `Java-<number>` identifiers against the stage 1 GitHub PR titles.
4. Match explicit `azure-resourcemanager-*` library names.
5. Match service-oriented phrases like `Java sdk review for compute limit api version 2026-06-01` back to the most plausible `azure-resourcemanager-*` PR title from the stage 1 dataset.

Preserve both the original thread text and the enrichment evidence. Do not replace the original body with the inferred PR title.

Persist the enriched dataset to:

```text
details\teams-enriched.json
```

If a thread has multiple plausible PR matches, keep all candidates in the enrichment file and note the ambiguity in `progress\stage-1.md`.

## Error handling

- If GitHub CLI returns no results unexpectedly, persist the exact query used in `progress\stage-1.md`.
- If Teams collection is blocked by EULA or authentication, stop and ask the user before continuing.
- If only part of the data is collected, keep the partial files and record exactly what is missing.
- If the Teams tool returns abbreviated text that drops the PR title or URL, record that as a collection limitation and run an enrichment pass using GitHub PR metadata before deciding the thread is out of scope.

## Stage notes

Write `progress\stage-1.md` with:
- data sources used
- exact period used
- file list created
- filtered GitHub total count and how it was computed
- missing data or collection gaps
- any authentication issues or manual follow-up needed
