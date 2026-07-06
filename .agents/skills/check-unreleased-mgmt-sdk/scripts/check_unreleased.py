"""Check azure-resourcemanager-* modules whose latest CHANGELOG entry is NOT
"(Unreleased)" (i.e. the top entry is a dated release with no pending unreleased
section), and group them by release month.

Reads file content from a git ref (default: the real Azure upstream main) rather
than the working tree, so a diverged local branch does not skew results.

Usage:
  python check_unreleased.py [--repo <path>] [--ref <git-ref>] [--csv <file>]

Defaults:
  --repo  current directory
  --ref   auto-detected Azure/azure-sdk-for-java main (see resolve_ref)

Exit code is always 0 on a successful scan; the report is printed to stdout.
"""
import argparse, os, re, subprocess, sys
from collections import defaultdict

HDR = re.compile(r"^##\s+(\S+)\s+\((.+?)\)\s*$")
CL = re.compile(r"azure-resourcemanager-[^/]+/CHANGELOG\.md$")
MOD = re.compile(r"(azure-resourcemanager-[^/]+)/CHANGELOG")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args],
                          capture_output=True, text=True, encoding="utf-8").stdout


def resolve_ref(repo, explicit):
    """Pick a git ref that points at the genuine Azure/azure-sdk-for-java main.

    Preference order:
      1. explicit --ref if provided
      2. a remote whose URL is github.com/Azure/azure-sdk-for-java, main branch
         (fetched fresh)
    Beware: in forks, `origin` may point at the fork, so we match by URL, not by
    remote name.
    """
    if explicit:
        return explicit
    remotes = git(repo, "remote", "-v")
    azure_remote = None
    for line in remotes.splitlines():
        parts = line.split()
        if len(parts) >= 2 and "(fetch)" in line:
            name, url = parts[0], parts[1]
            if re.search(r"github\.com[:/]Azure/azure-sdk-for-java(\.git)?$", url):
                azure_remote = name
                break
    if azure_remote:
        git(repo, "fetch", azure_remote, "main")
        return f"{azure_remote}/main"
    # last resort: local main
    return "main"


def first_entry(content):
    for line in content.splitlines():
        m = HDR.match(line.strip())
        if m:
            return m.group(1), m.group(2).strip()
    return None, None


def month_key(label):
    m = re.match(r"(\d{4})-(\d{2})-\d{2}", label)
    return f"{m.group(1)}-{m.group(2)}" if m else "unknown-date: " + label


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--ref", default=None)
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    ref = resolve_ref(repo, args.ref)
    head = git(repo, "log", "--oneline", "-1", ref).strip()
    print(f"Repo: {repo}")
    print(f"Ref:  {ref}  ({head})")

    listing = git(repo, "ls-tree", "-r", "--name-only", ref, "sdk/")
    paths = [p for p in listing.splitlines() if CL.search(p)]

    not_unreleased, unreleased, noheader = [], 0, []
    for p in paths:
        module = MOD.search(p).group(1)
        ver, label = first_entry(git(repo, "show", f"{ref}:{p}"))
        if ver is None:
            noheader.append(module)
        elif label.lower() == "unreleased":
            unreleased += 1
        else:
            not_unreleased.append((module, ver, label))

    print(f"\nTotal azure-resourcemanager-* modules: {len(paths)}")
    print(f"  latest entry = (Unreleased):            {unreleased}")
    print(f"  latest entry = dated release (flagged): {len(not_unreleased)}")
    print(f"  no parseable version header:            {len(noheader)}")

    groups = defaultdict(list)
    for module, ver, label in not_unreleased:
        groups[month_key(label)].append((label, module, ver))

    print("\n=== Modules whose latest entry is NOT 'Unreleased', grouped by month ===")
    for mk in sorted(groups):
        items = groups[mk]
        print(f"\n## {mk}  ({len(items)})")
        for label, module, ver in sorted(items):
            print(f"  {label}  {module}  (v{ver})")

    if noheader:
        print("\n=== No parseable header (review manually) ===")
        for module in sorted(noheader):
            print(" ", module)

    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["month", "date", "module", "version"])
            for module, ver, label in sorted(not_unreleased, key=lambda x: (x[2], x[0])):
                w.writerow([month_key(label), label, module, ver])
        print(f"\nCSV written: {args.csv}")


if __name__ == "__main__":
    main()
