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

Do not use sub-agent or parallel workflow, for tasks that potentially involve steps on local repository, as the local repository is a shared resource and may cause conflicts if multiple agents operate on it simultaneously. Always complete the review and merge process for one PR before starting another.

## Working directory

Use c:/github_lab/azure-sdk-for-java as the local repository.
- If the repository is missing, clone it first.
- Use git and GitHub CLI.

## Workflow

Copy this checklist and update it as work progresses:

```text
Automated PR review progress
- [ ] Confirm the PR matches the target pattern and is non-draft
- [ ] Inspect mergeability
- [ ] Inspect checks (CI results)
```

## Command to search for eligible PRs

```bash
gh pr list --state open --search "[AutoPR azure-resourcemanager- draft:false" --json number,title,isDraft,mergeable,mergeStateStatus"
```

## Mergability

If the branch of PR has conflict with main branch ("mergeable_state" is "dirty"), refer to [resolve-merge-conflict](./resolve-merge-conflict.md) to resolve the conflict.

## Checks

If the branch of PR has failed checks, refer to [inspect-checks](./inspect-checks.md) to investigate the failure.
