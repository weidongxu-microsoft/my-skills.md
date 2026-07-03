"""Stage 3 - compute metrics, charts, and per-language reports.

Usage: python compute_metrics.py <metric-folder>
  <metric-folder> defaults to the current directory. periodKey is derived from
  the folder name (self-serve-metric-<periodKey>).

Reads per language under details/<key>/:
  github-summary.json, github-pr-comments.json, teams-filtered.json
Writes result/<key>/{metrics.json, pr-communication-distribution.json,
  pr-communication-bar.png, report.md} plus cross-language summary +
  two cross-language charts under result/.

Language list is loaded from sdk-source.md headings if a language_keys.json is
present; otherwise falls back to the standard five keys. Adjust LANGS as needed.
"""
import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
det = os.path.join(root, "details")
res = os.path.join(root, "result")
periodKey = os.path.basename(root.rstrip("/\\")).replace("self-serve-metric-", "")

# (languageKey, displayName). Keep aligned with sdk-source.md.
LANGS = [
    ("java", "Java"),
    ("dotnet", ".NET"),
    ("python", "Python"),
    ("typescript-javascript", "TypeScript/JavaScript"),
    ("go", "Go"),
]

EXCLUDE_EXACT = {"Copilot", "copilot-pull-request-reviewer", "azure-sdk", "app/azure-sdk-automation"}

def is_bot(author):
    if author is None:
        return True
    if author in EXCLUDE_EXACT:
        return True
    if author.endswith("[bot]"):
        return True
    return False

def human_comment_count(rec):
    n = 0
    for c in rec.get("issueComments", []) or []:
        if not is_bot(c.get("author")):
            n += 1
    for c in rec.get("reviewComments", []) or []:
        if not is_bot(c.get("author")):
            n += 1
    return n

summary_rows = []

for key, disp in LANGS:
    gs = json.load(open(os.path.join(det, key, "github-summary.json"), encoding="utf-8"))
    cm = json.load(open(os.path.join(det, key, "github-pr-comments.json"), encoding="utf-8"))
    tf = json.load(open(os.path.join(det, key, "teams-filtered.json"), encoding="utf-8"))

    counts = sorted(human_comment_count(r) for r in cm)
    total = len(counts)
    mn = min(counts) if counts else 0
    mx = max(counts) if counts else 0
    avg = round(sum(counts) / total, 2) if total else 0.0

    dist = {}
    for c in counts:
        dist[c] = dist.get(c, 0) + 1
    dist_sorted = {str(k): dist[k] for k in sorted(dist)}

    retained = [t for t in tf if t.get("kept")]
    relatedPostCount = len(retained)
    human_replies = [t.get("humanReplyCount", 0) or 0 for t in retained]
    total_replies = [t.get("replyCount", 0) or 0 for t in retained]
    avg_human_replies = round(sum(human_replies) / relatedPostCount, 2) if relatedPostCount else 0.0
    avg_total_replies = round(sum(total_replies) / relatedPostCount, 2) if relatedPostCount else 0.0
    capped_any = any(t.get("replyCountCapped") for t in retained)

    metrics = {
        "language": disp,
        "languageKey": key,
        "periodKey": periodKey,
        "github": {
            "createdCount": gs["createdCount"],
            "mergedCount": gs["mergedCount"],
            "openCount": gs["openCount"],
            "totalFilteredAutoPrCount": gs["totalFilteredAutoPrCount"],
            "humanCommentMetrics": {
                "min": mn, "max": mx, "average": avg,
                "distribution": dist_sorted,
            },
        },
        "teams": {
            "relatedPostCount": relatedPostCount,
            "averageHumanRepliesPerPost": avg_human_replies,
            "averageTotalRepliesPerPost": avg_total_replies,
            "replyCountCappedForSomeThreads": capped_any,
        },
    }

    outdir = os.path.join(res, key)
    os.makedirs(outdir, exist_ok=True)
    json.dump(metrics, open(os.path.join(outdir, "metrics.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    json.dump({"language": disp, "totalFilteredAutoPrCount": total, "average": avg,
               "distribution": dist_sorted},
              open(os.path.join(outdir, "pr-communication-distribution.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    # per-language bar chart
    xs = sorted(dist)
    ys = [dist[x] for x in xs]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar([str(x) for x in xs], ys, color="#2b6cb0")
    for i, y in enumerate(ys):
        ax.text(i, y + 0.1, str(y), ha="center", va="bottom", fontsize=9)
    ax.set_xlabel("Human comment count on AutoPR")
    ax.set_ylabel("Number of AutoPRs")
    ax.set_title(f"{disp} AutoPR human communication distribution ({periodKey})\n"
                 f"Total filtered AutoPRs = {total}, average human comments/PR = {avg}")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "pr-communication-bar.png"), dpi=120)
    plt.close(fig)

    # report.md
    lines = []
    lines.append(f"# {disp} SDK self-serve metrics ({periodKey})\n")
    lines.append("## GitHub AutoPRs\n")
    lines.append(f"- Created in period: **{gs['createdCount']}**")
    lines.append(f"- Merged: **{gs['mergedCount']}**")
    lines.append(f"- Still open: **{gs['openCount']}**")
    lines.append(f"- Reporting ensemble (filtered created AutoPRs): **{gs['totalFilteredAutoPrCount']}**\n")
    lines.append("## Human communication per AutoPR\n")
    lines.append("Counts issue comments + review comments from non-bot authors "
                 "(excludes Copilot, copilot-pull-request-reviewer, *[bot], azure-sdk, app/azure-sdk-automation; "
                 "review submission events not counted).\n")
    lines.append(f"- Minimum: **{mn}**")
    lines.append(f"- Maximum: **{mx}**")
    lines.append(f"- Average: **{avg}**\n")
    lines.append("Distribution (comment count -> number of AutoPRs):\n")
    for k in xs:
        lines.append(f"- {k} -> {dist[k]} PRs")
    lines.append("")
    lines.append("![PR communication distribution](pr-communication-bar.png)\n")
    lines.append("## Teams (SDK-generation related threads)\n")
    lines.append(f"- Related top-level posts retained: **{relatedPostCount}**")
    lines.append(f"- Average human replies per post: **{avg_human_replies}**")
    lines.append(f"- Average total replies per post (incl. bot): **{avg_total_replies}**")
    if capped_any:
        lines.append("- Note: one or more threads had >=50 replies; the Graph reply page is capped, "
                     "so those reply counts are a lower bound.")
    lines.append("")
    lines.append("Retained threads:\n")
    for t in retained:
        lines.append(f"- {t.get('postTime','')} — {t.get('postAuthor','')}: {t.get('reason','')} "
                     f"(replies: {t.get('humanReplyCount',0)} human / {t.get('replyCount',0)} total)")
    lines.append("")
    open(os.path.join(outdir, "report.md"), "w", encoding="utf-8").write("\n".join(lines))

    summary_rows.append({
        "language": disp, "languageKey": key,
        "createdCount": gs["createdCount"], "mergedCount": gs["mergedCount"], "openCount": gs["openCount"],
        "totalFilteredAutoPrCount": gs["totalFilteredAutoPrCount"],
        "avgHumanCommentsPerPr": avg,
        "teamsRelatedPostCount": relatedPostCount,
        "avgHumanRepliesPerPost": avg_human_replies,
    })

# cross-language summary
json.dump({"periodKey": periodKey, "languages": summary_rows},
          open(os.path.join(res, "language-summary-metrics.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)

labels = [r["language"] for r in summary_rows]
pr_counts = [r["totalFilteredAutoPrCount"] for r in summary_rows]
avg_comm = [r["avgHumanCommentsPerPr"] for r in summary_rows]
teams_posts = [r["teamsRelatedPostCount"] for r in summary_rows]

# combined: PR count (bar) + avg human communication (line) dual axis
import numpy as np
x = np.arange(len(labels))
fig, ax1 = plt.subplots(figsize=(11, 6))
b = ax1.bar(x, pr_counts, width=0.55, color="#2b6cb0", label="Filtered AutoPR count")
for i, v in enumerate(pr_counts):
    ax1.text(i, v + 0.5, str(v), ha="center", va="bottom", fontsize=9)
ax1.set_ylabel("Filtered AutoPR count", color="#2b6cb0")
ax1.set_xticks(x); ax1.set_xticklabels(labels, rotation=15)
ax2 = ax1.twinx()
ax2.plot(x, avg_comm, color="#dd6b20", marker="o", linewidth=2, label="Avg human comments/PR")
for i, v in enumerate(avg_comm):
    ax2.text(i, v + 0.05, str(v), ha="center", va="bottom", color="#dd6b20", fontsize=9)
ax2.set_ylabel("Average human comments per PR", color="#dd6b20")
ax1.set_title(f"AutoPR count and average human communication per PR by language ({periodKey})")
fig.tight_layout()
fig.savefig(os.path.join(res, "language-pr-count-and-average-human-communication-bar.png"), dpi=120)
plt.close(fig)

# teams post count by language
fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(labels, teams_posts, color="#38a169")
for i, v in enumerate(teams_posts):
    ax.text(i, v + 0.1, str(v), ha="center", va="bottom", fontsize=9)
ax.set_ylabel("SDK-generation related Teams posts")
ax.set_title(f"SDK generation related Teams post count by language ({periodKey})")
plt.xticks(rotation=15)
fig.tight_layout()
fig.savefig(os.path.join(res, "language-teams-post-count-bar.png"), dpi=120)
plt.close(fig)

print("DONE", root, periodKey)
