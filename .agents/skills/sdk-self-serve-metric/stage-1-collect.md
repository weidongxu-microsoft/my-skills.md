# Stage 1 - Collect all source data

## Goal

Collect and persist all GitHub and Teams source data needed by later stages. This stage is about durable raw data capture, not final filtering or reporting.

## Inputs

- `periodStart`
- `periodEnd`
- `periodKey`
- repository root path
- `sdk-source.md`

## Outputs

- output folders under `self-serve-metric-<yyyymm>\`
- raw and normalized GitHub datasets per language
- a filtered GitHub collection summary with total counts per language
- raw and normalized Teams datasets per language
- enriched Teams datasets with inferred PR and library references when possible, per language
- `progress\stage-1.md`

## Checklist

```text
Stage 1 progress
- [ ] Normalize the requested period and create the output folders
- [ ] Load language entries from sdk-source.md
- [ ] Collect AutoPRs created within the period for each language
- [ ] Collect AutoPRs merged within the period for each language
- [ ] Collect currently open AutoPRs created within the period for each language
- [ ] Collect comments for the GitHub PRs in scope for each language
- [ ] Collect all posts and replies from each language Teams channel during the period
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
2. Load the language entries from `sdk-source.md`.
3. For each language entry, collect the GitHub created-period AutoPR cohort.
4. Apply the GitHub filters that exclude draft PRs and PRs closed without merging.
5. Derive the merged and currently-open subsets from that created-period cohort.
6. Compute and persist a filtered GitHub summary, including the total AutoPR count in scope.
7. Build the union of in-scope PR numbers and collect PR bodies plus comment data.
8. Collect the raw Teams channel threads and replies for the same period.
9. Enrich Teams threads with explicit or inferred PR references using the language-specific GitHub AutoPR dataset.
10. Persist raw outputs before creating normalized JSON files.
11. Write stage notes describing data coverage, blockers, and file locations.

## GitHub collection

For each language entry in `sdk-source.md`, use its GitHub repository, PR title pattern, and library pattern.

### Dataset A - AutoPRs created within the period

Search for PRs where:
- title contains the language entry's PR title pattern
- PR is not draft
- `createdAt` is within the requested period
- exclude PRs that are closed without being merged

Example search:

```bash
gh pr list --state all \
  --search "\"<pr-title-pattern>\" draft:false created:2026-05-01..2026-05-31" \
  --json number,title,url,author,createdAt,mergedAt,closedAt,state,isDraft,headRefOid \
  --repo <github-repository>
```

Then normalize the result by removing any PR where:
- `isDraft == true`, or
- `state == "CLOSED"` and `mergedAt` is empty

Persist to:

```text
details\<language-key>\github-prs-created.json
```

### Dataset B - Created-period AutoPRs that were merged

Build this dataset from dataset A only.

Keep PRs where:
- `mergedAt` is present

Persist to:

```text
details\<language-key>\github-prs-merged.json
```

### Dataset C - Currently open AutoPRs created within the period

Build this dataset from dataset A only.

Keep PRs where:
- `state == "OPEN"`
- `mergedAt` is empty

Persist to:

```text
details\<language-key>\github-prs-open.json
```

### Dataset D - PR body and comments

Because datasets B and C are subsets of dataset A, the union should normally equal dataset A. For every PR in that union, collect:
- PR body
- issue comments
- review comments or review-thread comments

Do not mix review submission events into the comment arrays used for the human comment count. If you collect review submissions for audit context, persist them separately from `issueComments` and `reviewComments`.

Prefer a single normalized file keyed by PR number. The normalized record should include:

```json
{
  "number": 12345,
  "url": "https://github.com/<org>/<repo>/pull/12345",
  "body": "...",
  "issueComments": [],
  "reviewComments": []
}
```

Useful commands:

```bash
gh pr view <PR_NUMBER> --json body,author,createdAt,mergedAt,closedAt,state,isDraft,title,url --repo <github-repository>

gh api repos/<org>/<repo>/issues/<PR_NUMBER>/comments

gh api repos/<org>/<repo>/pulls/<PR_NUMBER>/comments
```

If you need author metadata or threaded review context, use `gh api graphql`.

Persist to:

```text
details\<language-key>\github-pr-comments.json
```

For reproducibility, also persist the union PR number list to:

```text
details\<language-key>\github-pr-union.json
```

Also persist a filtered GitHub summary file that includes the total count label for in-scope AutoPRs:

```text
details\<language-key>\github-summary.json
```

Suggested shape:

```json
{
  "createdCount": 21,
  "mergedCount": 19,
  "openCount": 2,
  "unionCount": 21,
  "totalFilteredAutoPrCount": 21,
  "filters": {
    "excludeDraft": true,
    "excludeClosedUnmerged": true
  }
}
```

`totalFilteredAutoPrCount` should be computed after the draft and closed-unmerged filters are applied. Unless the user requests a different denominator, this is the created-period reporting ensemble, and `mergedCount` plus `openCount` must be interpretable as subsets of that same cohort.

## Teams collection

For each language entry, collect all top-level posts and replies from that language's Teams channel during the requested period before any filtering.

Channel URL:

```text
<teams-link>
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

Preserve `Azure/azure-rest-api-specs` PR links and validation-failure wording when present. These threads may later be retained even when they are not AutoPR review requests, because they can represent language-channel SDK validation or generation-failure triage for the same reporting period.

Prefer a prompt like:

```text
From the Teams channel at <channel-url>, list all top-level posts and all replies created between <periodStart> and <periodEnd>. Return structured JSON only. Preserve the full original text of each post and reply; do not summarize or paraphrase. For each thread include threadId, postAuthor, postTime, originalPostBody, normalizedPostBody if available, replyCount, replies[{author,time,originalBody,normalizedBody}], and any explicit links found in the post or replies.
```

Persist:
- the raw tool response to `details\<language-key>\teams-raw-response.txt`
- the normalized thread list to `details\<language-key>\teams-raw.json`

If the tool cannot return strict JSON, save the raw response first and then create a normalized JSON file beside it.

If the channel data is too large for one request:
1. split the period into smaller windows
2. collect each window separately
3. persist the per-window raw files in `details\<language-key>\teams-raw-parts\`
4. merge them into `details\<language-key>\teams-raw.json`

## Teams enrichment

After collecting the raw Teams threads, enrich them before stage 2 filtering for each language.

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
3. Match language-appropriate generation identifiers such as `Java-<number>`, `.NET-<number>`, `Python-<number>`, `JS-<number>`, or `Go-<number>` against the stage 1 GitHub PR titles.
4. Match explicit library names using the language entry's lib name pattern.
5. Match service-oriented phrases like `<language> sdk review for <service>` back to the most plausible PR title from the stage 1 dataset.

Preserve both the original thread text and the enrichment evidence. Do not replace the original body with the inferred PR title.

Persist the enriched dataset to:

```text
details\<language-key>\teams-enriched.json
```

If a thread has multiple plausible PR matches, keep all candidates in the enrichment file and note the ambiguity in `progress\stage-1.md`.

## Error handling

- If GitHub CLI returns no results unexpectedly, persist the exact query used in `progress\stage-1.md`.
- If Teams collection is blocked by EULA or authentication, stop and ask the user before continuing.
- If only part of the data is collected, keep the partial files and record exactly what is missing.
- If the Teams tool returns abbreviated text that drops the PR title or URL, record that as a collection limitation and run an enrichment pass using GitHub PR metadata before deciding the thread is out of scope.
- If a language entry in `sdk-source.md` is missing required fields, skip it and document the blocker instead of guessing.

## Stage notes

Write `progress\stage-1.md` with:
- language entries loaded from `sdk-source.md`
- data sources used
- exact period used
- per-language file list created
- per-language filtered GitHub total count and how it was computed
- missing data or collection gaps
- any authentication issues or manual follow-up needed
