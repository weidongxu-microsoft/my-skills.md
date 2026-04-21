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
- [ ] Verify Java package name for new library
- [ ] Inspect mergeability
- [ ] Inspect checks (CI results)
```

## Command to search for eligible PRs

```bash
gh pr list --state open --search "[AutoPR azure-resourcemanager- draft:false" --json number,title,isDraft,mergeable,mergeStateStatus" --repo Azure/azure-sdk-for-java
```

## Verify Java package name for new library

If the PR contains a new `sdk/<service>/<module>/pom.xml` file, rather than a modification of an existing one, refer to [Verify Java Package Name](./verify-java-package-name.md) to verify the Java package name.

## Mergeability is "dirty"

If the PR branch has conflicts with the main branch ("mergeable_state" is "dirty"), refer to [Resolve Merge Conflict](./resolve-merge-conflict.md) to resolve them.

## Failed checks

If the branch of PR has failed checks, refer to [Inspect Failed Checks](./inspect-failed-checks.md) to investigate the failure.
