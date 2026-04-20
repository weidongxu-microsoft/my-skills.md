# Target

Non-draft pull request on https://github.com/Azure/azure-sdk-for-java/pulls, with title contains `[AutoPR azure-resourcemanager-`.

Do not process draft pull request.

# Local repository

Use `c:/github_lab/azure-sdk-for-java` for process on PR branch. Clone it, if not exists.

You can use "git" and "GitHub CLI".

# Process

## Conflict with main branch

If the branch of PR has conflict with main branch ("mergeable_state" is "dirty"), you need to resolve the conflict.

Use the local repository to resolve the conflict.
- Get lastes main
- Checkout the branch
- Merge main
- Resolve conflict
- Commit and push
