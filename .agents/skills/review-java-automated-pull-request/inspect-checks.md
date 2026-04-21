# Inspect Checks

## Workflow

Copy this checklist and update it as work progresses:

```text
Automated PR review progress
- [ ] Check CI status for the PR
- [ ] If "Analyze" job fails on "Verify versions in POM file", follow [Update versions in POM](#update-versions-in-pom)
- [ ] If "Analyze" job fails on "Verify Swagger and TypeSpec Code Generation", follow [Investigate code generation](#investigate-code-generation)
- [ ] Commit and push the fix
- [ ] Wait for CI to complete (pass or error)
```

## Default process

1. Confirm the PR is eligible.
2. Check CI status for the PR.
3. If the "Analyze" job fails on the "Verify versions in POM file" step, follow [Update versions in POM](#update-versions-in-pom).
4. If "Analyze" job fails on "Verify Swagger and TypeSpec Code Generation", follow [Investigate code generation](#investigate-code-generation).
5. Wait for CI to complete (pass or error).

## Default commands

```bash
cd c:/github_lab/azure-sdk-for-java
gh pr checks <pr-number> --json name,state,link

# Get failed steps from Azure DevOps build timeline
az rest --method get --url "https://dev.azure.com/azure-sdk/<project-id>/_apis/build/builds/<build-id>/timeline?api-version=7.1" --query "records[?result=='failed'].{name: name, type: type, result: result, log: log}" -o json

# Get log for a specific failed step
az rest --method get --url "https://dev.azure.com/azure-sdk/<project-id>/_apis/build/builds/<build-id>/logs/<log-id>"

# Run sub-process

# Wait for CI to complete
gh pr checks <pr-number> --watch --fail-fast
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

## Investigate code generation

### Process

1. Ensure the local clone exists and update main.
2. Fetch and checkout latest main.
3. Check out the PR branch.
4. Merge origin/main into the PR branch.
5. Diff with main to find the project folder, it should be in the form of `sdk/<service>/<module>/`.
6. Run `tsp-client update` in project folder. This should re-generate the Java files.
6. Search the diff of re-generated code. See whether there is change of value in the assigment of `this.apiVersion = <api-version>` (change from `<current-api-version>` to `<latest-api-version>`) in a `##ClientImpl.java` file.
7. If there is such diff, check the PR to see if there is already comment like this: "The latest TypeSpec api-version is <latest-api-version>, but the specified api-version in this release request was <current-api-version>. Please pin api-version in TypeSpec to <current-api-version>". If no such comment, add one to remind the author.
8. If there is no such diff on the assignment of `api-version`, PAUSE AND ASK USER TO DECIDE WHAT TO DO.

### Commands

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

# Step 8: If no api-version diff, PAUSE AND ASK USER
```
