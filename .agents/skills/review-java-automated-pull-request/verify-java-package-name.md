# Verify Java Package Name

## Workflow

Copy this checklist and update it as work progresses:

```text
Automated PR review progress
- [ ] Check existing comments on Java package name
- [ ] Search "Board Review: Management Plane Namespace Review" issues in https://github.com/Azure/azure-sdk-pr/issues and https://github.com/Azure/azure-sdk/issues
- [ ] Find the Java module and package name from review issues
- [ ] When find matching review issue, also confirm that the issue was closed
```

## Default process

1. If there is already a comment in the PR in the form of `namespace review <url>`, skip the rest of this process. The package name has already been reviewed.
2. The new POM is `sdk/<service>/<module>/pom.xml`. Remember the `<service>` and `<module>`. You are going to verify whether this `<module>` is approved.
3. Search https://github.com/Azure/azure-sdk-pr/issues and https://github.com/Azure/azure-sdk/issues for GitHub issues that contain `Board Review: Management Plane Namespace Review` and `<service>` in the title.
4. For all such GitHub issues, read the issue description and search for an exact match of `<module> <package-name>`. The `<package-name>` would be `<module>` with all `-` replaced by `.` and prefixed with `com.`.
5. If the matching review issue is found but is still open, comment `namespace review not completed <url-to-review-issue>` and skip the rest of this process.
6. If no such review issue is found, log it and skip the rest of this process.
7. When the matching review issue is found, verify that the issue was closed. This signifies that the review was completed.
8. Comment `namespace review completed <url-to-review-issue>` in the PR.
9. Comment `/azp run prepare-pipelines` in the PR.
