# Stage 2 - Filter Teams threads

## Goal

Reduce each raw Teams dataset to the subset that is relevant to the current language entry's support communication, while preserving traceability back to the raw thread records.

## Inputs

- `details\<language-key>\teams-raw.json`
- `details\<language-key>\teams-enriched.json` if stage 1 created it
- stage 1 GitHub PR datasets for the same language

## Outputs

- `details\<language-key>\teams-filtered.json`
- optional `details\<language-key>\teams-filter-audit.json`
- `progress\stage-2.md`

## Checklist

```text
Stage 2 progress
- [ ] Load language entries from sdk-source.md
- [ ] Load the raw Teams dataset from stage 1 for each language
- [ ] Load the GitHub PR datasets from stage 1 for each language
- [ ] Filter Teams threads to those related to the current language entry
- [ ] Mark why each retained thread was kept
- [ ] Persist the filtered dataset and stage notes
```

## Filtering rules

Keep a Teams thread if any of the following is true:

1. The top-level post body matches the language entry's library or PR-title pattern
2. Any reply body matches the language entry's library or PR-title pattern
3. The top-level post or any reply contains a GitHub PR link in the language entry's repository
4. The linked PR number maps to a PR from stage 1 whose title matches the language entry's PR title pattern
5. The thread enrichment data maps the post or replies to an in-scope AutoPR title, generation identifier, or library from the language entry
6. The thread discusses an SDK validation or SDK generation failure for the current language and includes an `Azure/azure-rest-api-specs` PR link
7. The thread discusses an SDK validation or SDK generation failure for the current language and the text can be linked to a language-entry library even if the referenced PR is in `Azure/azure-rest-api-specs` rather than the SDK repository

Do not rely on keyword matching alone when a PR link is available. A thread with a PR link to an in-scope AutoPR should be kept even if the library name is not written explicitly in the text.

For rules 6 and 7, prefer keeping the thread when the post clearly describes language-channel triage of an SDK validation failure, SDK validation check failure, emitter crash, generator crash, or similar generation error for a spec PR in `Azure/azure-rest-api-specs`.

## Recommended normalized shape

Persist a filtered record like:

```json
{
  "threadId": "...",
  "kept": true,
  "reasons": [
    "body contains matching library pattern",
    "linked PR 49142 is an in-scope AutoPR",
    "thread text matched generation identifier to PR #49274"
  ],
  "linkedPrNumbers": [49142],
  "linkedPrTitles": [],
  "linkedLibraries": [],
  "matchEvidence": [],
  "postAuthor": "...",
  "postTime": "...",
  "postBody": "...",
  "replyCount": 3,
  "replies": []
}
```

Each retained thread should preserve enough evidence to explain why it was kept without rereading the raw source. Every retained thread must carry `replyCount` (total replies incl. bot) and `humanReplyCount` (non-bot replies) so stage 3 can compute both average-reply denominators; set `replyCountCapped: true` when total replies reach the reply-page cap of 50.

## Reusable builder

Rather than hand-writing the filtered file, record only the Stage 2 decisions and let the shared script assemble the output:

1. For each language, write `details\<language-key>\teams-decisions.json`, a JSON object mapping the retained `threadId` to `{"reason", "replyCount", "humanReplyCount"}` (total/human reply counts from the `/messages/{id}/replies` fetch).
2. Run `scripts/build_teams_filtered.py <metric-root>` (optionally pass specific language keys). It reads `teams-raw.json` + `teams-decisions.json`, keeps only threads with `createdInPeriod == true`, and writes `teams-filtered.json` with every in-period thread flagged `kept` (retained ones also carry `reason`, `replyCount`, `humanReplyCount`, `replyCountCapped`, `postAuthor`, `postTime`). This is the exact shape `scripts/compute_metrics.py` (and `stage3.py`) consume.

The resulting `teams-filtered.json` retains all in-period threads with a `kept` boolean (not just retained ones), keeping the discard decisions auditable in one file.

## Workflow

1. Load the raw Teams threads.
2. Load the stage 1 GitHub PR datasets for the same language and build a lookup by PR number, title, generation identifier, and library name.
3. Inspect each thread for keyword evidence, PR-link evidence, `Azure/azure-rest-api-specs` validation-failure evidence, and stage-1 enrichment evidence.
4. Keep threads that are clearly related to an in-scope AutoPR even when the original post omitted the explicit URL.
5. Keep threads that are clearly language-relevant SDK validation or generation-failure triage for an `Azure/azure-rest-api-specs` PR even when no SDK-repo PR link is present.
6. Record the decisions in `teams-decisions.json` and run `scripts/build_teams_filtered.py` to persist `teams-filtered.json`.

## Output files

Persist the filtered dataset to:

```text
details\<language-key>\teams-filtered.json
```

Persist an optional audit file with discarded threads and reasons if it helps:

```text
details\<language-key>\teams-filter-audit.json
```

## Error handling

- If a Teams thread references a PR link that cannot be resolved, record the unresolved link in `progress\stage-2.md`.
- If a thread is ambiguous, prefer retaining the candidate matches in an audit field and document the ambiguity.
- Do not mutate the raw dataset during filtering.

If a thread appears to describe an in-scope AutoPR review request but lacks the explicit PR link, prefer matching it through stage-1 enrichment instead of dropping it immediately.

If a thread appears to describe an SDK validation failure or generation failure for the current language and includes an `Azure/azure-rest-api-specs` PR link, prefer retaining it with explicit evidence rather than dropping it because the link is not in the SDK repository.

## Stage notes

Write `progress\stage-2.md` with:
- filtering rules applied
- per-language number of raw threads
- per-language number of retained threads
- edge cases
- threads kept only because of linked PR evidence
- threads kept because of `Azure/azure-rest-api-specs` validation-failure evidence

## Stage 2.5 - Split the shared "SDK release support" channel

The shared **"SDK release support"** channel (collected in Stage 1 to
`details\sdk-release-support\teams-raw.json`) is **not** language-specific and is
**not** 1:1 with the created-in-period AutoPR cohort. Its threads are release-time
help requests: some name a service, many are general tooling/process (release
planner, agent auth, doc-publishing). Release effort is also **time-decoupled** from
the base metric — a thread may reference a service whose AutoPR was created weeks
earlier or that has no in-period AutoPR at all. Do **not** fold this channel into the
per-service review bars wholesale.

Instead, split it against the services already charted this period:

1. Build `charted_services` = the set of service tokens produced by the AutoPR pass
   (Stage 1 comments) plus the per-language Teams pass (Stage 2). This is the
   **period-anchored** vocabulary.
2. For each release-support thread, resolve its service (via `[AutoPR <lib>]`, a
   known service-name keyword in the subject+body, or a longest-match against
   `charted_services`).
   - **Found** (resolves to a service in `charted_services`) -> feeds a **3rd
     "release-support" bar** on that service in Stage 3.
   - **Not found** (resolves to a service with no in-period AutoPR/Teams activity, or
     to no service at all) -> goes to a concise **unattributed summary**, never a bar.
3. The not-found threads are tagged with a `category`:
   - `named-service-not-in-period-cohort` — names a real service, but it is outside
     the period's created-in-period cohort (temporal mismatch).
   - `tooling/process` — general release tooling/process, not a specific service.

This split is implemented inline by `scripts/group_by_service.py` (Stage 3), which
reads `details\sdk-release-support\teams-raw.json`, emits the found threads as the 3rd
bar, and writes the not-found threads to
`result\release-support-unattributed-<periodKey>.json` (total human replies, per-
`category` counts, and per-thread subject + humanReplyCount + resolvedService). No
separate stage-2.5 file is produced; the split is auditable from that JSON.
