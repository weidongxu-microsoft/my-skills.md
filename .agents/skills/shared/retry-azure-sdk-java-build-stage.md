# Retry Intermittent Build Test Checks

Use this only for `Azure/azure-sdk-for-java` pull request workflows when exactly 1 or 2 failed checks are named `Build Test ...`. Treat broader or mixed failures as non-intermittent and continue with normal investigation or skip logic in the calling skill.

## Process

1. Use `gh pr checks` to confirm the failures are limited to `Build Test ...`.
2. Identify the Azure DevOps build ID for the failed `java - pullrequest` run.
3. Retry the failed Azure DevOps `Build` stage.
4. Confirm the failed check returns to `pending`.
5. Wait for CI to complete and continue only if all checks pass.

## Retry endpoint

```text
PATCH https://dev.azure.com/azure-sdk/public/_apis/build/builds/<build-id>/stages/Build?api-version=7.1
```

Request body:

```json
{"state":"retry","forceRetryAllJobs":false}
```

Authentication details:
- Azure DevOps resource ID for token acquisition: `499b84ac-1321-427f-aa17-267ca6975798`
- Use `az rest` first.
- If `az rest` fails with a JSON parsing error such as `TF400898` / `JsonReaderException`, use `curl` with a bearer token from `az account get-access-token`.

## Commands

```bash
gh pr checks <pr-number> --json name,state,link --repo Azure/azure-sdk-for-java

az rest --resource 499b84ac-1321-427f-aa17-267ca6975798 \
  --method patch \
  --url "https://dev.azure.com/azure-sdk/public/_apis/build/builds/<build-id>/stages/Build?api-version=7.1" \
  --headers "Content-Type=application/json" \
  --body '{"state":"retry","forceRetryAllJobs":false}'

# If az rest hits TF400898 / JsonReaderException, get a bearer token:
az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798 --query accessToken -o tsv

# Then re-run the PATCH with curl using that token
curl -sS -X PATCH \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  --data "{\"state\":\"retry\",\"forceRetryAllJobs\":false}" \
  "https://dev.azure.com/azure-sdk/public/_apis/build/builds/<build-id>/stages/Build?api-version=7.1"

gh pr checks <pr-number> --watch --fail-fast --repo Azure/azure-sdk-for-java
```
