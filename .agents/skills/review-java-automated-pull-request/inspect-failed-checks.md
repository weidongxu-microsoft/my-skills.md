# Inspect Failed Checks

## Workflow

Copy this checklist and update it as work progresses:

```text
Inspect failed checks progress
- [ ] Check CI status for the PR
- [ ] If "Analyze" job fails on "Verify versions in POM file", follow [Update versions in POM](#update-versions-in-pom)
- [ ] If "Analyze" job fails on "Verify Swagger and TypeSpec Code Generation", follow [Investigate code generation](#investigate-code-generation)
- [ ] Commit and push the fix
- [ ] Wait for CI to complete (pass or error)
```

## Default process

1. Check CI status for the PR.
2. If the "Analyze" job fails on the "Verify versions in POM file" step, follow [Update versions in POM](#update-versions-in-pom).
3. If "Analyze" job fails on "Verify Swagger and TypeSpec Code Generation", follow [Investigate code generation](#investigate-code-generation).
4. Wait for CI to complete (pass or error).

## Default commands

```bash
gh pr checks <pr-number> --json name,state,link --repo Azure/azure-sdk-for-java

# Get failed steps from Azure DevOps build timeline
az rest --method get --url "https://dev.azure.com/azure-sdk/<project-id>/_apis/build/builds/<build-id>/timeline?api-version=7.1" --query "records[?result=='failed'].{name: name, type: type, result: result, log: log}" -o json

# Get log for a specific failed step
az rest --method get --url "https://dev.azure.com/azure-sdk/<project-id>/_apis/build/builds/<build-id>/logs/<log-id>"

# Run sub-process

# Wait for CI to complete
gh pr checks <pr-number> --watch --fail-fast --repo Azure/azure-sdk-for-java
```

# Update Versions in POM

## Process

1. Ensure the local clone exists and update main.
2. Fetch and checkout latest main.
3. Check out the PR branch.
4. Merge origin/main into the PR branch.
5. Run `python eng/versioning/update_versions.py --sr`. It should update the POM in the project.
6. Verify that only the "pom.xml" file gets updated.
7. Commit and push.

## Commands

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

# Investigate Code Generation

## Process

1. Ensure the local clone exists and update main.
2. Fetch and checkout latest main.
3. Check out the PR branch.
4. Merge origin/main into the PR branch.
5. Diff with main to find the project folder; it should be in the form of `sdk/<service>/<module>/`.
6. Run `tsp-client update` in the project folder. This should regenerate the Java files.
7. Search the regenerated code diff. Check whether there is a change in the assignment of `this.apiVersion = <api-version>` (from `<current-api-version>` to `<latest-api-version>`) in a `##ClientImpl.java` file.
8. If there is such a diff, check the PR to see if there is already a comment like this: "The latest TypeSpec api-version is <latest-api-version>, but the specified api-version in this release request was <current-api-version>. Please pin api-version in TypeSpec tspconfig.yaml to <current-api-version>". If no such comment exists, add one to remind the author.
9. If there is no such diff on the assignment of `api-version`, STOP AND ASK USER TO DECIDE WHAT TO DO.

## Commands

```bash
# Steps 1-4: Clone, update main, checkout PR branch, merge main
if [ ! -d c:/github_lab/azure-sdk-for-java ]; then
  git clone https://github.com/Azure/azure-sdk-for-java.git c:/github_lab/azure-sdk-for-java
fi

cd c:/github_lab/azure-sdk-for-java
git fetch origin
git checkout main
git pull --ff-only origin main
gh pr checkout <pr-number>
git merge origin/main

# Step 5: Find the project folder from the diff
git diff --name-only origin/main

# Step 6: Run tsp-client update in the project folder
cd sdk/<service>/<module>
tsp-client update
cd c:/github_lab/azure-sdk-for-java

# Step 7: Search for api-version change in generated ClientImpl.java
git diff -- "sdk/<service>/<module>/**/*ClientImpl.java" | grep "this.apiVersion"

# Step 7 continued: Check existing PR comments
gh pr view <pr-number> --comments --json comments --jq '.comments[].body'

# Step 8: If no api-version diff, STOP AND ASK USER
```
