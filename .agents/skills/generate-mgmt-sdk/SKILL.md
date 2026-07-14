---
name: generate-mgmt-sdk
description: '**WORKFLOW SKILL** - Generate (regenerate) an Azure Java management SDK via the Azure DevOps "SDK Generation - Java" pipeline (definitionId 7421). Use for requests like "generate mgmt sdk from specs PR <specs-pr>", "regen sdk for <sdk-pr> using HEAD of specs PR <specs-pr>", or "generate SDK <sdk> via pipeline".'
---

# Generate Management SDK (via pipeline)

Use this skill to generate or regenerate an Azure Java management SDK by running the
Azure DevOps pipeline, not by generating/building locally.

Reference guide: https://github.com/weidongxu-microsoft/typespec-sdk-releases/blob/main/AGENTS.md#guide-on-task-generate-sdk-sdk-via-pipeline

## Request patterns

Typical requests:

- `generate mgmt sdk from specs PR <specs-pr>`
- `regen sdk for <sdk-pr> using HEAD of specs PR <specs-pr>`
- `generate SDK <sdk> via pipeline`
- `regen it again with updated HEAD` (re-run using the latest HEAD of the same specs PR)

## Scope

This skill runs the **"SDK Generation - Java"** pipeline (Azure DevOps, `internal` project,
`definitionId = 7421`, YAML `eng/pipelines/spec-gen-sdk.yml`).

It covers:

1. resolving inputs from the specs PR and (optional) target SDK PR
2. queueing pipeline 7421 with the correct template parameters and specs commit
3. verifying the queued parameters
4. waiting for the run to complete
5. finding the resulting `[AutoPR ...]` SDK PR and opening it in the browser

The pipeline itself creates the AutoPR; this skill only approves the existing AutoPR.

## Working rules

- Prefer `gh` CLI for GitHub operations.
- Prefer `az rest` for Azure DevOps REST calls (let Azure CLI handle the token). Use
  `--resource 499b84ac-1321-427f-aa17-267ca6975798` and `--header "Content-Type=application/json"`.

## Key facts

- Pipeline: `SDK Generation - Java`, `definitionId = 7421`, project `internal`.
- Azure DevOps org: `https://dev.azure.com/azure-sdk`.
- Auth resource (AAD app id for Azure DevOps): `499b84ac-1321-427f-aa17-267ca6975798`.
- Runs API: `https://dev.azure.com/azure-sdk/internal/_apis/pipelines/7421/runs?api-version=7.1`.
- Build API (status/timeline): `https://dev.azure.com/azure-sdk/internal/_apis/build/builds/{buildId}?api-version=7.1`.

## Checklist

Copy this checklist and update it during execution:

```text
Generate management SDK progress
- [ ] Get specs PR HEAD SHA (commit-sha) and branch
- [ ] Get target SDK PR branch (sdkauto/azure-resourcemanager-...) if an SDK PR is given
- [ ] Resolve ConfigPath (tspconfig.yaml relative path) from specs PR
- [ ] Confirm az CLI is logged in
- [ ] Queue pipeline 7421 with template parameters + specs commit
- [ ] Verify queued parameters and specs commit version
- [ ] Wait for the run to complete
- [ ] Find the resulting [AutoPR ...] SDK PR and open in browser
```

## Step 1: Resolve inputs

### Specs PR (`from specs PR {specs-pr}`)

Get the HEAD SHA (`commit-sha`) and branch of the specs PR:

```powershell
gh pr view <specs-pr> --repo Azure/azure-rest-api-specs --json headRefName,headRefOid,state,files
```

- `headRefOid` → `commit-sha` (the specs commit the pipeline builds from)
- `headRefName` → specs branch name
- For **"regen with updated HEAD"**, re-fetch `headRefOid` to pick up new commits.

### Target SDK PR (`to sdk PR {sdk-pr}`)

If an SDK PR is given, get its branch (should be `sdkauto/azure-resourcemanager-...`):

```powershell
gh pr view <sdk-pr> --repo Azure/azure-sdk-for-java --json headRefName,state,title
```

- `headRefName` → `target-sdk-repo-branch` (passed as `SdkRepoBranch`)
- The regen updates this branch; a CLOSED SDK PR is typically reopened by the new run.

### ConfigPath (tspconfig.yaml)

Determine the `tspconfig.yaml` path from the specs PR changed files, or from the known
service folder `specification/{service}/**`. Read it at the specs PR HEAD to confirm the
Java emitter config:

```powershell
gh api "repos/Azure/azure-rest-api-specs/contents/<path-to>/tspconfig.yaml?ref=<commit-sha>" `
  --jq '.content' | ForEach-Object { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }
```

`ConfigPath` is the relative path from the specs repo root, e.g.
`specification/containerservice/resource-manager/Microsoft.ContainerService/preparedimagespecification/tspconfig.yaml`.

## Step 2: Confirm auth

```powershell
az account show --query "{name:name, user:user.name}" -o json
```

## Step 3: Queue the pipeline

Pipeline `7421` template parameters (from `eng/pipelines/spec-gen-sdk.yml`):

| Parameter | Value |
| --- | --- |
| `SdkRepoBranch` | `target-sdk-repo-branch` (omit/`main` if no SDK PR) |
| `ConfigType` | `TypeSpec` |
| `ConfigPath` | tspconfig.yaml relative path |
| `ApiVersion` | `none` |
| `SdkReleaseType` | `none` |
| `CreatePullRequest` | `true` |

> **`SdkReleaseType`**: use `none` generally (for both initial generation and regeneration) — the pipeline decides `beta` vs `stable` automatically from whether the api-version is a preview. Only pass an explicit `beta`/`stable` to override that automatic decision.

Build the specs commit into `resources.repositories.self` so the pipeline checks out the
specs PR HEAD. Write the body to a temp file to avoid quoting issues, then POST:

```json
{
  "resources": {
    "repositories": {
      "self": {
        "refName": "refs/heads/<specs-branch>",
        "version": "<commit-sha>"
      }
    }
  },
  "templateParameters": {
    "SdkRepoBranch": "<target-sdk-repo-branch>",
    "ConfigType": "TypeSpec",
    "ConfigPath": "<config-path>",
    "ApiVersion": "none",
    "SdkReleaseType": "beta",
    "CreatePullRequest": true
  }
}
```

```powershell
az rest --method post `
  --url "https://dev.azure.com/azure-sdk/internal/_apis/pipelines/7421/runs?api-version=7.1" `
  --resource "499b84ac-1321-427f-aa17-267ca6975798" `
  --headers "Content-Type=application/json" `
  --body "@<path-to-body.json>" `
  --query "{id:id, state:state, version:resources.repositories.self.version, params:templateParameters, web:_links.web.href}" -o json
```

## Step 4: Verify queued parameters

From the POST response, confirm:

- `templateParameters` match the intended `ConfigPath`, `SdkRepoBranch`, and
  `CreatePullRequest = true` (`ApiVersion = none`, `SdkReleaseType = none`)
- `resources.repositories.self.version` equals `commit-sha`
- `state` is `inProgress`

Report the run id and web URL:
`https://dev.azure.com/azure-sdk/internal/_build/results?buildId=<id>`

## Step 5: Wait for completion

Poll the build status (or create a scheduled watcher for long runs — the run typically takes
~10 minutes):

```powershell
az rest --method get `
  --url "https://dev.azure.com/azure-sdk/internal/_apis/build/builds/<id>?api-version=7.1" `
  --resource "499b84ac-1321-427f-aa17-267ca6975798" `
  --query "{status:status, result:result}" -o json
```

- Wait until `status` is `completed`.
- `result` of `succeeded` or `partiallySucceeded` is acceptable (`partiallySucceeded` is
  common and normal for SDK generation).

## Step 6: Find and open the AutoPR

Find the AutoPR on the target SDK branch:

```powershell
gh pr list --repo Azure/azure-sdk-for-java `
  --head "<target-sdk-repo-branch>" --state all `
  --json number,title,state,url,updatedAt
```

- The PR title looks like `[AutoPR <sdk-package>]...-<buildId>`; the newest run's build id
  should appear in the title of the OPEN PR.
- A regen updates the same branch: the previous run's PR may be CLOSED and superseded by a
  freshly (re)opened PR referencing the new build id.

Open it in the browser:

```powershell
Start-Process "https://github.com/Azure/azure-sdk-for-java/pull/<pr-number>"
```

## Stop conditions

Stop and ask the user if:

- the `tspconfig.yaml` path cannot be resolved confidently
- multiple `tspconfig.yaml` candidates exist for the service
- the target SDK PR branch is not a `sdkauto/azure-resourcemanager-...` branch
- the pipeline run fails (`result = failed`)
- no matching `[AutoPR ...]` PR can be found after the run completes
