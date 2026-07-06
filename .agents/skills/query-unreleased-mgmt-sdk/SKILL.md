---
name: query-unreleased-mgmt-sdk
description: Lists Azure Java management SDK modules (azure-resourcemanager-*) whose latest CHANGELOG entry is a dated release rather than "(Unreleased)", grouped by release month. Use for requests like "query unreleased mgmt sdk", "which azure-resourcemanager modules have no Unreleased section", or "list mgmt modules whose last changelog item is not Unreleased".
---

# Query Unreleased Management SDK

Report which `azure-resourcemanager-*` modules in `azure-sdk-for-java` have a
CHANGELOG whose **latest (top) entry is a dated release** — i.e. the newest
`## <version> (<label>)` header is `(YYYY-MM-DD)` and **not** `(Unreleased)`.
These modules have no pending "Unreleased" section (usually released with no new
dev/beta cycle opened yet). Results are grouped by release month.

## Scope

This skill is for:
- the `azure-sdk-for-java` repository, `sdk/**/azure-resourcemanager-*/CHANGELOG.md`
- management-plane libraries only (module name starts with `azure-resourcemanager-`)

This skill is not for:
- data-plane / client libraries (non `azure-resourcemanager-*`)
- editing changelogs or cutting releases

## Local repository and ref

- Run the check in the local clone at **`c:/github_lab/azure-sdk-for-java`**.
- Always evaluate against **main from the Azure org** (`https://github.com/Azure/azure-sdk-for-java`, branch `main`), never the working tree and never a fork's `main`.
- The check reads file content from a git ref, so a diverged local branch or dirty working tree does not affect results.

### Why ref, not working tree

A local clone may be checked out on a feature branch that is diverged many
commits from `main`. Reading from the ref (`git show <ref>:<path>`) guarantees
the report reflects the real published state.

### Why match the remote by URL, not by name

`origin` is **not** guaranteed to be the Azure org repo:
- In `c:/github_lab/azure-sdk-for-java`, `origin` is `Azure/azure-sdk-for-java` (correct).
- In `c:/github/azure-sdk-for-java`, `origin` is a personal fork and `upstream` is the Azure org.

The script resolves the ref by finding the remote whose fetch URL matches
`github.com/Azure/azure-sdk-for-java`, fetches its `main`, and uses `<remote>/main`.
Do not assume `origin/main`.

## Workflow

Run the bundled script from the skill folder:

```powershell
$env:PYTHONIOENCODING="utf-8"
python .agents/skills/query-unreleased-mgmt-sdk/scripts/check_unreleased.py --repo c:/github_lab/azure-sdk-for-java
```

The script will:
1. Auto-detect the Azure-org remote by URL and `git fetch <remote> main`.
2. Print the resolved ref and its HEAD commit (verify it looks like real main).
3. Enumerate `sdk/**/azure-resourcemanager-*/CHANGELOG.md` at that ref.
4. For each, read the first `## <version> (<label>)` header.
5. Flag modules where `<label>` is a date (not `Unreleased`).
6. Group flagged modules by release month and print the report.

Optional flags:
- `--ref <git-ref>` — override the auto-detected ref (e.g. a tag or specific commit).
- `--csv <file>` — also write `month,date,module,version` rows to a CSV.

## Output interpretation

- **Total** = all `azure-resourcemanager-*` modules scanned.
- **(Unreleased)** = modules with a pending unreleased section at the top (the common case).
- **dated release (flagged)** = the modules to report; these are the answer.
- **no parseable header** = CHANGELOG without a recognizable `## version (label)`
  first header; review these manually (should normally be zero).

Always report the resolved ref/commit alongside the counts so the reader can
confirm the check ran against current Azure-org main.

## Success criteria

- The resolved ref is a `main` from `Azure/azure-sdk-for-java`, freshly fetched.
- Every `azure-resourcemanager-*` module is classified (no silent omissions).
- Flagged modules are listed with their release date and version, grouped by month.
