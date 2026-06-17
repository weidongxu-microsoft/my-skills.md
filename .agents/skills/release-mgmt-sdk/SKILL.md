---
name: release-mgmt-sdk
description: '**WORKFLOW SKILL** - Release Azure Java management SDKs using Azure DevOps pipelines, then track status in the root java-sdk-release-status files. Use for requests like "release mgmt sdk for <service>", "release Java mgmt sdk", or "check release status for <service>".'
---

# Release Management SDK

Use this skill to release Azure Java management SDKs, based on the workflow in `weidongxu-microsoft/typespec-sdk-releases` and the local tracker files in this repository.

## Request patterns

Typical requests include:

- `release mgmt sdk for <service>`
- `release Java mgmt sdk for <service>`
- `check release status for <service>`

`<service>` may be a service name, release-plan row, spec project path, or Java module path.

## Scope

This skill is for **Azure Java management SDK** release work only.

It covers:

1. locating the Java module
2. releasing the SDK through the service pipeline
3. merging the follow-up `Increment versions` PR
4. checking the latest `CHANGELOG.md` release date
5. updating the local tracker files in this repo

It does **not** cover:

- SDK generation workflow
- broad migration or emitter fixes in specs/emitter repos
- non-management SDKs

## Required repositories

- SDK repo: `C:\github_lab\azure-sdk-for-java`
- Specs repo: `C:\github_lab\azure-rest-api-specs`

Call them **sdk repo** and **specs repo**.

When doing local work in sdk repo, refresh local `main` first.

## Working rules

- Do not create PRs locally unless the workflow explicitly requires it.
- Prefer `gh` CLI for GitHub operations.
- Prefer `az rest` or authenticated REST for Azure DevOps operations.
- Work one service at a time when local repositories or the same PR/pipeline are involved.

## Checklist

Copy this checklist and update it during execution:

```text
Release management SDK progress
- [ ] Identify the target service row in the local tracker
- [ ] Confirm the Java module path
- [ ] Refresh local sdk repo main if local inspection is needed
- [ ] Check the latest changelog entry
- [ ] Abort if the latest changelog entry is `Unreleased`
- [ ] Release the SDK via service pipeline
- [ ] Create a scheduled watcher for the release pipeline run
- [ ] Wait until `Signing` is completed and succeeded
- [ ] If a `Build` stage or check fails, retry the failed check
- [ ] Approve the pending release gate after `Signing` succeeds
- [ ] Create a scheduled watcher for the `Releasing: 1 libraries` release stage
- [ ] Wait until `Releasing: 1 libraries` succeeds or fails
- [ ] Review / approve / merge the Increment versions PR
- [ ] Refresh changelog status from local sdk repo
- [ ] Update java-sdk-release-status.csv
- [ ] Update java-sdk-release-status.md
```

## Step 1: Identify the target row

Find the service in:

- `java-sdk-release-status.csv`
- `java-sdk-release-status.md`

Use the row to determine:

- release plan
- spec project path
- Java module path
- current Java PR / release state

If the row has no Java module path yet, infer it from `tspconfig.yaml` as described below, then add it to the markdown tracker.

## Step 2: Infer or verify the Java module path

Read `tspconfig.yaml` and inspect:

- `parameters.service-dir`
- `options."@azure-tools/typespec-java".service-dir` if present
- `options."@azure-tools/typespec-java".emitter-output-dir`

From these, determine the Java module path in sdk repo, typically:

```text
sdk/<service>/<azure-resourcemanager-package>
```

If the path is non-obvious, verify using `tsp-location.yaml` or the package contents in sdk repo, then record it in `java-sdk-release-status.md`.

## Step 3: Check the latest changelog entry

Read the `CHANGELOG.md` for the Java module from **`Azure/azure-sdk-for-java` on `main`** and determine the latest entry.

For this skill:

- if the latest entry is `Unreleased`, **abort**
- if the latest entry has a date, continue with release workflow

## Step 4: Release the SDK

Use this when the user asks to release an SDK.

### Find the service pipeline

Find pipeline:

`java - {service}`

in Azure DevOps internal builds, where `{service}` is derived from the Java module path:

```text
sdk/<service>/<sdk-package>
```

### Run the release pipeline

1. queue the pipeline
2. if it uses `templateParameters`, set only:
   - `release_{sdk-package}` = `true`
   - all others = `false`
3. if it has no template parameters, run it directly
4. verify the queued parameters are correct
5. open the pipeline run in the browser
6. wait for completion

### After queueing the run

Immediately create a scheduled task to monitor the pipeline run.

The scheduled task should:

1. check whether the `Signing` stage exists
2. wait until `Signing` is `completed` and `succeeded`
3. inspect the `Build` stage / checks for failures while waiting
4. if a `Build` check fails and it is retryable, retry the failed check
5. continue watching until `Signing` is successful or a non-retryable failure occurs

If `Signing` succeeds and the approval step is complete, stop this first schedule and hand off to a second schedule for the same release pipeline's `Releasing: 1 libraries` stage.

### After `Signing` succeeds

Check whether the release stage is blocked on a pending approval.

1. Query pending approvals:

```bash
GET https://dev.azure.com/{organization}/{project}/_apis/pipelines/approvals?api-version=7.1-preview.1
```

2. Find the approval whose pipeline owner matches the current build/run.
3. Approve it using the same payload shape as the existing Java automation utility.

Use `curl.exe` with a raw JSON body:

```powershell
$token = az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv
$approvalId = '<approval-id>'
$body = '[{\"approvalId\":\"' + $approvalId + '\",\"status\":4,\"comment\":\"\"}]'
$uri = 'https://dev.azure.com/azure-sdk/internal/_apis/pipelines/approvals/' + $approvalId + '?api-version=7.2-preview'

curl.exe -sS -X PATCH $uri `
  -H \"Authorization: Bearer $token\" `
  -H \"Content-Type: application/json\" `
  --data-binary $body
```

The response should show the approval status as `approved`.

### After the approval is sent

Immediately create a second scheduled task dedicated to the still-running `Releasing: 1 libraries` release stage.

The second scheduled task should:

1. wait until `Releasing: 1 libraries` is `completed`
2. stop and report if `Releasing: 1 libraries` fails
3. not retry failures in this stage
4. if the stage succeeds, continue directly to the Increment versions PR workflow
5. stop itself after either success-with-handoff or failure

## Step 5: Process the Increment versions PR

After a successful release pipeline:

1. find the corresponding `Increment versions` PR
2. confirm checks pass
3. resolve Copilot-only review threads if needed
4. ensure no unresolved human review threads remain
5. approve the PR
6. merge it
The existing `merge-increment-versions-pr` skill is the reference workflow for this step.

## Step 6: Refresh changelog state

After release actions, read the `CHANGELOG.md` for the Java module from **`Azure/azure-sdk-for-java` on `main`** and determine:
- latest entry
- whether it is dated or `Unreleased`

Update the snapshot table in `java-sdk-release-status.md` when it materially changes.

## Step 7: Update local tracker files

Update both:

- `java-sdk-release-status.csv`
- `java-sdk-release-status.md`

Keep them aligned.

### CSV conventions

- `java_pr_created`: `yes/no`
- `java_pr_merged`: `yes/no`
- `java_sdk_released`: `yes/no`
- `state`: use values like `not created`, `draft`, `merged`, `completed`

### Markdown conventions

Keep:

1. the major actions section near the top
2. the changelog snapshot table
3. the detailed row table with module path and notes

Log notable actions such as:

- merged PRs
- release runs
- no-op generated PRs that were intentionally closed

## Useful commands

### GitHub PR search

```bash
gh pr list --state all --search "Increment versions" --json number,title,state,url --repo Azure/azure-sdk-for-java
```

### Azure DevOps auth

```bash
az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798
```

### Inspect latest changelog heading

```bash
Select-String -Path <CHANGELOG.md> -Pattern '^##\s+(.+)$' | Select-Object -First 1
```

## Stop conditions

Stop and ask the user if:

- you cannot identify the Java module path confidently
- the pipeline parameters are ambiguous
- the latest changelog entry is `Unreleased`
- the release pipeline exposes multiple plausible `release_*` switches
