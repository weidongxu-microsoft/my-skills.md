---
name: review-java-automated-pull-request
description: Reviews and updates non-draft automated pull requests for Azure Java management libraries in azure-sdk-for-java. Use when a pull request title contains [AutoPR azure-resourcemanager-], especially to inspect the PR, sync with main, resolve merge conflicts, commit, and push.
---

# Review Java Automated Pull Request

Use this skill only when all of the following are true:
- The repository is Azure/azure-sdk-for-java.
- The pull request is not a draft.
- The title contains `[AutoPR azure-resourcemanager-]`.

Do not use this skill for draft or unrelated pull requests.

## Working directory

Use c:/github_lab/azure-sdk-for-java as the local repository.
- If the repository is missing, clone it first.
- Use git and GitHub CLI.

## Workflow

Copy this checklist and update it as work progresses:

```text
Automated PR review progress
- [ ] Confirm the PR matches the target pattern and is non-draft
- [ ] Ensure the local repo exists and main is current
- [ ] Check out the PR branch locally
- [ ] Inspect mergeability
- [ ] If mergeable_state is dirty, merge main into the branch
- [ ] Resolve all conflicts and verify no conflict markers remain
- [ ] Commit and push the fix
```

## Default process

1. Confirm the PR is eligible.
2. Ensure the local clone exists and update main.
3. Check out the PR branch.
4. If the PR merge state is dirty, merge origin/main into the PR branch.
5. Resolve conflicts carefully.
6. Verify the branch is conflict-free.
7. Commit and push.

## Default commands

```bash
if [ ! -d c:/github_lab/azure-sdk-for-java ]; then
  git clone https://github.com/Azure/azure-sdk-for-java.git c:/github_lab/azure-sdk-for-java
fi

cd c:/github_lab/azure-sdk-for-java
git fetch origin
git checkout main
git pull --ff-only origin main
gh pr checkout <pr-number>
gh pr view <pr-number> --json isDraft,title,mergeable
git merge origin/main
```

## Conflict resolution rules

- Resolve only the conflicts needed to unblock the PR branch.
- Preserve the generated PR intent while keeping compatibility with main.
- Before committing, verify there are no remaining merge markers such as <<<<<<<, =======, or >>>>>>>.
- Commit and push only after the working tree is fully resolved.

## Validation loop

1. Check PR state.
2. Merge main only when needed.
3. Verify there are no unmerged files.
4. Commit and push.
5. Re-check the PR state when possible.
