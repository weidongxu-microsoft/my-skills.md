# Review Changes

## Check the package api-version and stable-vs-preview consistency

Find the api-version(s) the package is generated against:

1. Read `CHANGELOG.md` (e.g. `Package api-version 2026-03-01-preview.`).
2. Else use the `apiVersions` property in `src/main/resources/META-INF/<module>_metadata.json` — an object keyed by RP namespace (e.g. `"apiVersions": {"Microsoft.AzureArcData": "2026-03-01-preview"}`), possibly with multiple entries.

If **any** api-version is `-preview`, the package must be **beta**, not stable (GA). Flag a stable-version-on-preview-api mismatch and ask the author for clarification.

## Watch for incorrect LRO headers and response models

There should be no new `<ClientMethod>Response` and `<ClientMethod>Headers` model classes where the `<ClientMethod>Headers` model contains `location` or `retry-after`.

The generation of these models usually means a long-running operation is incorrectly specified in TypeSpec, or even a normal GET/POST response is being treated like an LRO.

## Scan CHANGELOG.md early for suspicious generation

`CHANGELOG.md` is often the fastest place to spot suspicious generation:

- duplicated generated release lines or multiple package `api-version` entries in the same release.
  This usually happens when the service triggers SDK generation multiple times for different `api-version` values. Leave a comment asking for clarification.

## Treat public surface breaking changes as a major review trigger

Major review triggers include:

- renamed or removed public methods;
- return type changes on existing methods;
- new generated headers or response types that imply wrong LRO semantics.

## Ask before approval

If you think the PR can be approved, ask the user for confirmation before taking action.

## Report concerns clearly

If there is a concern about the PR, notify the user with the suspected pattern, the affected public API, and whether it looks like a spec-generation issue.
