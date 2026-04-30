---
name: review-java-automated-pull-request
description: Reviews and updates non-draft automated pull requests for Azure Java management libraries in azure-sdk-for-java. Use when a pull request title contains [AutoPR azure-resourcemanager-, especially to inspect the PR, sync with main, resolve merge conflicts, commit, and push.
---

# Review Java Automated Pull Request

Use this skill only when all of the following are true:
- The repository is Azure/azure-sdk-for-java.
- The pull request is not a draft.
- The title contains `[AutoPR azure-resourcemanager-`.

Do not use this skill for draft or unrelated pull requests.

Do not process any further if the PR author is not `azure-sdk`.

Do not merge the PR.

Do not use a sub-agent or parallel workflow for tasks that involve the local repository, as it is a shared resource and may cause conflicts if multiple agents operate on it simultaneously. Always complete the review process for one PR before starting another.

## Working directory

Use c:/github_lab/azure-sdk-for-java as the local repository.
- If the repository is missing, clone it first.
- Use git and GitHub CLI.

## Workflow

Copy this checklist and update it as work progresses:

```text
Automated PR review progress
- [ ] Confirm the PR matches the target pattern and is non-draft
- [ ] Confirm PR author is `azure-sdk`
- [ ] Check review progress from memory (if HEAD SHA matches, skip it and move to the next PR)
- [ ] Check PR description contains `Release Plan link: <url>` (warn if missing, continue)
- [ ] Verify Java package name for new library
- [ ] Inspect mergeability
- [ ] Inspect checks (CI results)
```

## Memorize review progress

Recall memory "pr-reviewed" to get the review progress. It should contain a list of PR numbers, the HEAD SHA of the commit reviewed, and the review status.

After reviewing all PRs, save a final summary to memory "pr-reviewed" with the review progress. It should persist
- PR number
- HEAD SHA of the PR
- review status (e.g. "ready for merge", "pending peer review", "has check failures", "has merge conflicts")

## Command to search for eligible PRs

```bash
# headRefOid is the HEAD SHA of the PR
gh pr list --state open --search "[AutoPR azure-resourcemanager- draft:false" --json number,title,headRefOid,isDraft,mergeable,mergeStateStatus --repo Azure/azure-sdk-for-java

# List PRs with failed checks
gh pr list --state open --search "[AutoPR azure-resourcemanager- draft:false status:failed" --json number,title  --repo Azure/azure-sdk-for-java
```

## Confirm PR author is `azure-sdk`

Retrieve the PR author and verify it is `azure-sdk`:

```bash
gh pr view <PR_NUMBER> --json author --repo Azure/azure-sdk-for-java --jq '.author.login'
```

If the author is not `azure-sdk`, skip this PR and report the unexpected author — do not process it further.

## Check PR description contains a Release Plan link

Retrieve the PR body and check for a line matching `Release Plan link: <url>`:

```bash
gh pr view <PR_NUMBER> --json body --repo Azure/azure-sdk-for-java --jq '.body'
```

If no `Release Plan link:` line is found in the description, log a warning (e.g. "WARNING: No Release Plan link found in PR #<PR_NUMBER> description") and continue the review process.

## Verify Java package name for new library

Use the following command to check whether the PR adds a new `pom.xml` or modifies an existing one:

```bash
gh api repos/Azure/azure-sdk-for-java/pulls/<PR_NUMBER>/files \
  --jq '.[] | select(.filename | endswith("pom.xml")) | {filename, status}'
```

If `status` is `"added"`, the pom.xml is new — refer to [Verify Java Package Name](./verify-java-package-name.md) to verify the Java package name.
If `status` is `"modified"`, it is an existing library update and no package name verification is needed.

## Mergeability is "dirty"

If the PR branch has conflicts with the main branch ("mergeable_state" is "dirty"), refer to [Resolve Merge Conflict](./resolve-merge-conflict.md) to resolve them.

## Failed checks

If the branch of PR has failed checks, refer to [Inspect Failed Checks](./inspect-failed-checks.md) to investigate the failure.
