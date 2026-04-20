# Inspect Checks

## Workflow

Copy this checklist and update it as work progresses:

```text
Automated PR review progress
- [ ] Check CI status for the PR
- [ ] If "Analyze" job fails on "Verify versions in POM file", follow [Update versions in POM](#update-versions-in-pom)
- [ ] Commit and push the fix
- [ ] Wait for CI to complete (pass or error)
```

## Default process

1. Confirm the PR is eligible.
2. Check CI status for the PR.
3. If the "Analyze" job fails on the "Verify versions in POM file" step, follow [Update versions in POM](#update-versions-in-pom).
4. Wait for CI to complete (pass or error).

## Default commands

```bash
cd c:/github_lab/azure-sdk-for-java
gh pr checks <pr-number>
gh run view <run-id> --log-failed
```

## Update versions in POM

### Process

1. Ensure the local clone exists and update main.
2. Fetch and checkout latest main.
3. Check out the PR branch.
4. Merge origin/main into the PR branch.
5. Run `python eng/versioning/update_versions.py --sr`. It should update the POM in project.
6. Verify that only "pom.xml" file get updated.
7. Commit and push.

### Commands

```bash
if [ ! -d c:/github_lab/azure-sdk-for-java ]; then
  git clone https://github.com/Azure/azure-sdk-for-java.git c:/github_lab/azure-sdk-for-java
fi

cd c:/github_lab/azure-sdk-for-java
git fetch origin
git checkout main
git pull --ff-only origin main
gh pr checkout <pr-number>
git merge origin/main
python eng/versioning/update_versions.py --sr
git diff --name-only
git add -A
git commit -m "Update versions in POM"
git push
gh pr checks <pr-number> --watch --fail-fast
```
