---
name: merge-increment-versions-pr
description: Merges non-draft "Increment versions" pull requests in azure-sdk-for-java after validating checks pass and only version/changelog files are modified. Use when a pull request title contains "Increment versions".
---

# Merge Increment Versions PR

Use this skill only when all of the following are true:
- The repository is Azure/azure-sdk-for-java.
- The pull request is not a draft.
- The title contains `Increment versions`.

Do not use this skill for draft or unrelated pull requests.

Do not use a sub-agent or parallel workflow for tasks that involve the GitHub API, as concurrent operations on the same PR may cause conflicts. Always complete the merge process for one PR before starting another.

## Command to search for eligible PRs

```bash
gh pr list --state open --search "Increment versions draft:false" --json number,title,isDraft,mergeable,mergeStateStatus --repo Azure/azure-sdk-for-java
```

## Workflow

Copy this checklist and update it as work progresses:

```text
Increment versions PR merge progress
- [ ] Find eligible PRs (title contains "Increment versions", non-draft)
- [ ] Confirm all CI checks pass
- [ ] Confirm only allowed files are modified
- [ ] Resolve all Copilot review comments
- [ ] Confirm no unresolved review comments from human users
- [ ] Approve and merge the PR
```

Process each eligible PR one at a time following the steps below.

## Step 1: Confirm all CI checks pass

Retrieve the check runs for the PR's head commit:

```bash
gh pr checks <PR_NUMBER> --repo Azure/azure-sdk-for-java
```

All checks must have a `pass` or `success` conclusion. If any check is still pending, wait and retry. If any check has failed, skip this PR and report the failure — do not merge it.

## Step 2: Confirm only allowed files are modified

Retrieve the list of files changed in the PR:

```bash
gh pr diff <PR_NUMBER> --name-only --repo Azure/azure-sdk-for-java
```

Every file in the diff must match one of these patterns:
- `**/version_client.txt`
- `**/pom.xml`
- `**/CHANGELOG.md`

If any file outside these patterns is present, skip this PR and report the unexpected file — do not merge it.

## Step 3: Resolve all Copilot review comments

List all review threads on the PR. For each unresolved review comment authored by `Copilot` (or `github-actions[bot]` acting as Copilot), resolve the thread using the GitHub GraphQL API:

```bash
# List review threads to find Copilot's unresolved comments
gh api graphql -f query='
{
  repository(owner: "Azure", name: "azure-sdk-for-java") {
    pullRequest(number: <PR_NUMBER>) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          comments(first: 1) {
            nodes {
              author {
                login
              }
            }
          }
        }
      }
    }
  }
}'

# Resolve each unresolved Copilot thread by its thread ID
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {threadId: "<THREAD_ID>"}) {
    thread {
      id
      isResolved
    }
  }
}'
```

Resolve all unresolved threads where the first comment's author login is `Copilot` or `copilot-pull-request-reviewer[bot]`.

## Step 4: Confirm no unresolved comments from human users

After resolving Copilot threads, check whether any review threads from human users remain unresolved. Use the same GraphQL query from Step 3 and inspect all threads where `isResolved` is `false` and the author login is **not** `Copilot`, `copilot-pull-request-reviewer`, or any known bot (logins ending in `[bot]`).

If any such thread exists, skip this PR and report the unresolved human comment — do not merge it.

## Step 5: Approve and merge the PR

Approve the PR:

```bash
gh pr review <PR_NUMBER> --approve --repo Azure/azure-sdk-for-java
```

Merge the PR using squash merge with admin privileges:

```bash
gh pr merge <PR_NUMBER> --squash --admin --repo Azure/azure-sdk-for-java
```

Report the result after merging.
