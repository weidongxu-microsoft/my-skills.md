---
name: release-mgmt-sdk
description: '**WORKFLOW SKILL** - Release Azure Java management SDKs using Azure DevOps pipelines. Use for requests like "release mgmt sdk for <service>" or "release mgmt sdk for <module>" where <service> is a service folder name and <module> is a Java module name like azure-resourcemanager-*.'
---

# Release Management SDK

Use this skill to release Azure Java management SDKs.

## Request patterns

Typical requests:

- `release mgmt sdk for <service>` — where `<service>` is a service folder name (e.g. `cognitiveservices`)
- `release mgmt sdk for <module>` — where `<module>` is a Java module name (e.g. `azure-resourcemanager-cognitiveservices`)

## Scope

This skill is for **Azure Java management SDK** release work only.

It covers:

1. locating the Java module
2. releasing the SDK through the service pipeline
3. merging the follow-up `Increment versions` PR
4. checking the latest `CHANGELOG.md` release date
5. opening the Sonatype Central artifact link for the released module

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

- Prefer `gh` CLI for GitHub operations.
- Prefer `az rest` or authenticated REST for Azure DevOps operations.
- Work one service at a time when local repositories or the same PR/pipeline are involved.

## Checklist

Copy this checklist and update it during execution:

```text
Release management SDK progress
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
- [ ] Open the Sonatype Central artifact link for the released module
```

## Step 1: Infer or verify the Java module path

The request is typically `release mgmt sdk for <service>` or `release mgmt sdk for <module>`.

- If the argument looks like a Java module name (e.g. starts with `azure-resourcemanager-`), use it directly as the module.
- If the argument looks like a service folder name, look in `sdk/<service>/` in the SDK repo for directories matching `azure-resourcemanager-*`. Each such directory is a candidate module.
  - If exactly one candidate is found, use it.
  - If multiple candidates are found, ask the user to clarify which module to release.

The resolved Java module path in the SDK repo is:

```text
sdk/<service>/<azure-resourcemanager-package>
```

## Step 2: Check the latest changelog entry

Read the `CHANGELOG.md` for the Java module from **`Azure/azure-sdk-for-java` on `main`** and determine the latest entry.

For this skill:

- if the latest entry is `Unreleased`, **abort**
- if the latest entry has a date, continue with release workflow

## Step 3: Release the SDK

Use this when the user asks to release an SDK.

### Find the service pipeline

First check whether a module-specific pipeline exists for the service:

`java - azure-resourcemanager-{service}`

If it exists, use that pipeline. Otherwise, fall back to:

`java - {service}`

in Azure DevOps internal builds, where `{service}` is derived from the Java module path:

```text
sdk/<service>/<sdk-package>
```

### Determine release parameters

Do not rely on the pipeline preview API alone to discover `release_*` parameters.

First query the pipeline definition and note its `yamlFilename`:

```powershell
$token = az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv
$definition = Invoke-RestMethod -Method Get -Uri "https://dev.azure.com/azure-sdk/internal/_apis/build/definitions/{pipelineId}?api-version=7.1" -Headers @{ Authorization = "Bearer $token" }
$definition.process.yamlFilename
```

Then use the Azure DevOps Contribution `HierarchyQuery` API with `onlyFetchTemplateParameters = true` to retrieve the resolved template parameters before queueing any build:

```powershell
$token = az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv
$body = @{
  contributionIds = @("ms.vss-build-web.pipeline-run-parameters-data-provider")
  dataProviderContext = @{
    properties = @{
      pipelineId = {pipelineId}
      sourceBranch = "refs/heads/main"
      sourceVersion = ""
      onlyFetchTemplateParameters = $true
      retrieveOptions = 1
      templateParameters = @{}
      sourcePage = @{
        url = "https://dev.azure.com/azure-sdk/internal/_build?definitionId={pipelineId}&_a=summary"
        routeId = "ms.vss-build-web.pipeline-details-route"
        routeValues = @{
          project = "internal"
          viewname = "details"
          controller = "ContributedPage"
          action = "Execute"
          serviceHost = "0fb41ef4-5012-48a9-bf39-4ee3de03ee35 (azure-sdk)"
        }
      }
    }
  }
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod -Method Post -Uri "https://dev.azure.com/azure-sdk/_apis/Contribution/HierarchyQuery/project/590cfd2a-581c-4dcb-a12e-6568ce786175?api-version=7.1-preview.1" -Headers @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" } -Body $body
$templateParameters = $response.dataProviders."ms.vss-build-web.pipeline-run-parameters-data-provider".templateParameters
$templateParameters | ConvertTo-Json -Depth 10
```

Look for a `release_{safeName}` parameter in `templateParameters`. The `safeName` is typically the artifact name with hyphens removed and lowercased (e.g., `azure-resourcemanager-standbypool` → `release_azureresourcemanagerstandbypool`).

If the Contribution API returns no `release_*` parameter, optionally cross-check the `ci.yml` referenced by `yamlFilename`, but prefer the Contribution API result for queue-time parameter discovery.

**Enumerate ALL `release_*` parameters, not just the target.** A service pipeline can build several artifacts, each with its own `release_{safeName}` parameter, and **their defaults are not always `false`**. For example, `sdk/batch/ci.yml` defines `release_azurecomputebatch` with `default: true`. If you queue with only the target set to `"true"`, every other `release_*` parameter falls back to its ci.yml default, so a sibling defaulting to `true` will be released unintentionally (and can fail the `Releasing` stage with "already been deployed", or worse, publish an artifact you did not intend to release).

Therefore, from the `templateParameters` (and/or `ci.yml`), list **every** `release_*` parameter. The target is the one matching your module's `safeName`; all others are non-target.

### Run the release pipeline

1. If the `ci.yml` has a `release_{safeName}` parameter:
   - Queue with `templateParameters`:
     ```powershell
     $body = @{ templateParameters = @{
         release_{targetSafeName} = "true"
         # explicitly pin ALL other release_* params to false (never rely on their ci.yml defaults):
         release_{otherSafeName1} = "false"
         release_{otherSafeName2} = "false"
     } } | ConvertTo-Json -Depth 5
     $run = Invoke-RestMethod -Method Post -Uri 'https://dev.azure.com/azure-sdk/internal/_apis/pipelines/{id}/runs?api-version=7.1' -Headers @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" } -Body $body
     ```
2. If the `ci.yml` has **no** `release_` parameters:
   - Queue with empty body:
     ```powershell
     $body = @{} | ConvertTo-Json
     $run = Invoke-RestMethod -Method Post -Uri 'https://dev.azure.com/azure-sdk/internal/_apis/pipelines/{id}/runs?api-version=7.1' -Headers @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" } -Body $body
     ```
3. **Verify the queued parameters** by retrieving the run and checking `templateParameters`:
   ```powershell
   $buildUri = "https://dev.azure.com/azure-sdk/internal/_apis/build/builds/$($run.id)?api-version=7.1"
   $build = Invoke-RestMethod -Uri $buildUri -Headers @{ Authorization = "Bearer $token" } -Method Get
   $build.templateParameters | ConvertTo-Json
   ```
   - The target `release_{safeName}` must be `"true"` and **every other `release_*` parameter must be `false`** in the retrieved build. Note the casing: values you explicitly set appear lowercase (`"true"`/`"false"`), whereas a parameter left at its pipeline default appears capitalized (`"True"`/`"False"`) — a capitalized `"True"` on a non-target parameter means it defaulted in and the run is wrong.
   - If any non-target `release_*` is not `false`, or the target is not `"true"`, the run was queued incorrectly
   - Cancel the incorrect run and re-queue with correct parameters
4. Open the pipeline run in the browser
5. Wait for completion

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

Find and approve the pending release gate.

1. Get the build timeline and find the in-progress Checkpoint:

```powershell
$token = az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv
$timeline = Invoke-RestMethod -Method Get -Uri "https://dev.azure.com/azure-sdk/internal/_apis/build/builds/{buildId}/timeline?api-version=7.1" -Headers @{ Authorization = "Bearer $token" }
$checkpoint = $timeline.records | Where-Object { $_.type -eq 'Checkpoint' -and $_.state -eq 'inProgress' }
```

2. Find the Checkpoint.Approval record (child of the checkpoint):

```powershell
$approval = $timeline.records | Where-Object { $_.parentId -eq $checkpoint.id -and $_.type -eq 'Checkpoint.Approval' -and $_.state -eq 'inProgress' }
$approvalId = $approval.id
```

3. Approve it using a temp file to avoid escaping issues:

```powershell
$body = '[{"approvalId":"' + $approvalId + '","status":4,"comment":""}]'
$bodyFile = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($bodyFile, $body, [System.Text.Encoding]::UTF8)
$uri = "https://dev.azure.com/azure-sdk/internal/_apis/pipelines/approvals/$approvalId?api-version=7.2-preview"
curl.exe -sS -X PATCH $uri -H "Authorization: Bearer $token" -H "Content-Type: application/json" --data-binary "@$bodyFile"
Remove-Item $bodyFile
```

The response should show the approval status as `approved`.

**Important:** The approval ID is NOT found via the `/pipelines/approvals` API list. It must be extracted from the build timeline as a `Checkpoint.Approval` record.

### After the approval is sent

Immediately create a second scheduled task dedicated to the still-running `Releasing: 1 libraries` release stage.

The second scheduled task should:

1. wait until `Releasing: 1 libraries` is `completed`
2. stop and report if `Releasing: 1 libraries` fails
3. not retry failures in this stage
4. if the stage succeeds, continue directly to the Increment versions PR workflow
5. stop itself after either success-with-handoff or failure

## Step 4: Process the Increment versions PR

After a successful release pipeline:

1. find the corresponding `Increment versions` PR
2. confirm checks pass
3. resolve Copilot-only review threads if needed
4. ensure no unresolved human review threads remain
5. approve the PR
6. merge it
The existing `merge-increment-versions-pr` skill is the reference workflow for this step.

## Step 5: Open the Sonatype Central artifact link

After the release stage succeeds and the Increment versions PR is handled, provide the
Sonatype Central (Maven Central) link for the released module so the user can verify
publication:

```text
https://central.sonatype.com/artifact/com.azure.resourcemanager/<module-name>
```

For example, `azure-resourcemanager-cognitiveservices`:

```text
https://central.sonatype.com/artifact/com.azure.resourcemanager/azure-resourcemanager-cognitiveservices
```

Note: it can take some time after the release stage completes for the package to appear
on Sonatype Central.

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
