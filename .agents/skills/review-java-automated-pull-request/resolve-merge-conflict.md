# Resolve Merge Conflict

## Workflow

Copy this checklist and update it as work progresses:

```text
Automated PR review progress
- [ ] Confirm the PR matches the target pattern and is non-draft
- [ ] Ensure the local repo exists and main is current
- [ ] Check out the PR branch locally
- [ ] If mergeable_state is dirty, merge main into the branch
- [ ] Resolve all conflicts and verify no conflict markers remain
- [ ] Commit and push the fix
- [ ] Wait for CI to complete (pass or error)
```

## Default process

1. Confirm the PR is eligible.
2. Ensure the local clone exists and update main.
3. Fetch and checkout latest main.
4. Check out the PR branch.
5. If the PR merge state is dirty, merge origin/main into the PR branch.
6. Resolve conflicts carefully.
7. Verify the branch is conflict-free.
8. Commit and push.
9. Wait for CI to complete (pass or error).

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
gh pr checks <pr-number> --watch --fail-fast
```

## Conflict resolution rules

- The conflict file should typically only be the "eng/versioning/version_client.txt". If you see lots of conflict files, STOP AND ASK USER.
- Resolve only the conflicts needed to unblock the PR branch.
- Preserve the generated PR intent while keeping compatibility with main.
- Before committing, verify there are no remaining merge markers such as <<<<<<<, =======, or >>>>>>>.
- Commit and push only after the working tree is fully resolved.
