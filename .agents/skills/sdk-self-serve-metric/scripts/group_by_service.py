"""Group AutoPR human comments and Teams human replies by Azure service.

Usage: python group_by_service.py <metric-folder> [--top N]
  <metric-folder> defaults to the current directory. periodKey is derived from
  the folder name (self-serve-metric-<periodKey>).

Reads per language under details/<key>/:
  github-prs-created.json  (number -> title, for the service token)
  github-pr-comments.json  (per-PR issue/review comments -> human count)
  teams-filtered.json      (kept threads -> humanReplyCount + service token)

The service token is derived from the AutoPR library name embedded in the PR
title ("[AutoPR <lib>]...") and in the kept Teams thread "reason". The library
name differs per language, so norm_lib() canonicalizes it to a language-neutral
token so the same service lines up across languages.

Writes under result/:
  service-communication-<periodKey>.json  (raw per service x lang x channel)
  service-communication-<periodKey>.png   (grouped stacked bar: per service two
      bars - AutoPR human comments and Teams human replies - each stacked by
      language)

Language list is auto-discovered from the details/ subfolders present, so it
adapts to the languages in sdk-source.md and to the per-run .NET folder name
("net" or "dotnet") without editing this file.
"""
import json, os, re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.getcwd()
TOP = 20  # default: keep the most-discussed services readable, fold the rest
if "--top" in sys.argv:
    TOP = int(sys.argv[sys.argv.index("--top") + 1])

det = os.path.join(root, "details")
res = os.path.join(root, "result")
periodKey = os.path.basename(root.rstrip("/\\")).replace("self-serve-metric-", "")

DISPLAY_NAMES = {
    "java": "Java", "dotnet": ".NET", "net": ".NET", "python": "Python",
    "typescript-javascript": "TypeScript/JavaScript", "go": "Go",
}
ORDER = ["java", "dotnet", "net", "python", "typescript-javascript", "go"]
COLORS = {
    "java": "#2b6cb0", "dotnet": "#6b46c1", "net": "#6b46c1", "python": "#38a169",
    "typescript-javascript": "#dd6b20", "go": "#e53e3e",
}

# Java abbreviates some service segments; map them onto the fuller token that
# the other languages use so they line up in the same service bucket. Period-
# specific one-off merges do NOT belong here - put them in a per-run
# service-aliases.json in the metric folder (see load of PERIOD_ALIAS below).
ALIAS = {
    "containerservicepreparedimgspec": "containerservicepreparedimagespecification",
    "napsteromniagent": "napsteromniagentapi",
}

EXCLUDE_EXACT = {"Copilot", "copilot-pull-request-reviewer", "azure-sdk", "app/azure-sdk-automation"}
UNATTRIBUTED = "(unattributed-triage)"

# Optional per-run, one-off service merges: a JSON object {"<from>": "<to>"} in
# <metric-folder>/service-aliases.json. Keys/values are matched against the final
# normalized service token. Use this for period-specific special cases (e.g. two
# tokens that happen to be the same service that month) instead of hardcoding
# them into ALIAS above.
PERIOD_ALIAS = {}
_pa_path = os.path.join(root, "service-aliases.json")
if os.path.exists(_pa_path):
    PERIOD_ALIAS = {k.lower(): v.lower() for k, v in json.load(open(_pa_path, encoding="utf-8")).items()}

# Freeform service names that appear in Teams triage-thread reasons but differ
# from the AutoPR-derived token; map the normalized freeform form -> canonical.
SERVICE_ALIASES = {
    "napster": "napsteromniagentapi",
    "bulkactions": "computebulkactions",
    "computebulkactions": "computebulkactions",
    "resiliencemanagement": "resiliencemanagement",
    "azureresiliencemanagement": "resiliencemanagement",
    "trafficmanager": "trafficmanager",
    "networkcloud": "networkcloud",
    "computeschedule": "computeschedule",
    "billingtrust": "billingtrust",
    "microsoftvalidate": "microsoftvalidate",
}
# Named services (not necessarily present in the AutoPR vocabulary) to look for
# anywhere in a triage reason when there is no usable parenthetical hint.
NAMED_KEYWORDS = {
    "billingtrust": "billingtrust",
    "microsoftvalidate": "microsoftvalidate",
    "trafficmanager": "trafficmanager",
    "resiliencemanagement": "resiliencemanagement",
}
# Parenthetical contents that are not a service (dates handled separately).
NON_SERVICE_PARENS = {"enum", "specmigration", "specmigrations"}


def is_bot(author):
    return author is None or author in EXCLUDE_EXACT or author.endswith("[bot]")


def load(path):
    return json.load(open(path, encoding="utf-8"))


def norm_lib(lib):
    """Canonicalize a per-language AutoPR library name to a neutral token."""
    s = lib.strip()
    for pat in (r"^azure[.\-]resourcemanager[.\-]", r"^azure[.\-]mgmt[.\-]?",
                r"^sdk-resourcemanager/", r"^@azure[/\-]arm[/\-]?"):
        s = re.sub(pat, "", s, flags=re.I)
    s = s.lower()
    if "/" in s:  # Go path form: <service>/arm<submodule>
        segs = [re.sub(r"^arm", "", x) for x in s.split("/") if x]
        out = segs[0]
        for nxt in segs[1:]:
            if nxt.startswith(out) or out.startswith(nxt):
                out = nxt if len(nxt) > len(out) else out
            else:
                out = out + nxt
        s = out
    s = re.sub(r"[^a-z0-9]", "", s)
    s = ALIAS.get(s, s)
    return PERIOD_ALIAS.get(s, s)


def service_from(text):
    m = re.search(r"\[AutoPR ([^\]]+)\]", text or "")
    return norm_lib(m.group(1)) if m else None


def service_from_reason(reason, known):
    """Resolve a service token from a Teams thread reason.

    Order: explicit [AutoPR <lib>]; then a "(Service)" parenthetical hint; then a
    substring match against the known AutoPR service vocabulary (longest wins);
    then a small named-keyword fallback. Returns None if nothing sensible matches
    (those threads stay in the unattributed-triage bucket).
    """
    reason = reason or ""
    svc = service_from(reason)
    if svc:
        return svc
    # explicit parenthetical hint, e.g. "... (Napster)", "... (NetworkCloud)"
    for grp in re.findall(r"\(([^)]+)\)", reason):
        g = grp.strip()
        if "#" in g or re.match(r"^\d{4}-\d{2}-\d{2}$", g):
            continue  # PR/issue ref or a date, not a service
        key = re.sub(r"[^a-z0-9]", "", g.lower())
        if not key or key in NON_SERVICE_PARENS or re.match(r"^[a-z]{0,4}\d+$", key):
            continue
        return SERVICE_ALIASES.get(key, ALIAS.get(key, key))
    # substring scan against the known AutoPR service vocabulary (longest match)
    low = re.sub(r"[^a-z0-9]", "", reason.lower())
    best = None
    for tok in known:
        if len(tok) >= 5 and tok in low and (best is None or len(tok) > len(best)):
            best = tok
    if best:
        return best
    # named services that may not be in the vocabulary
    for kw, canon in NAMED_KEYWORDS.items():
        if kw in low:
            return canon
    return None


def discover_langs(details_dir):
    present = [d for d in os.listdir(details_dir) if os.path.isdir(os.path.join(details_dir, d))]
    ordered = [k for k in ORDER if k in present]
    ordered += sorted(k for k in present if k not in ORDER)
    return ordered


def human_comment_count(rec):
    n = 0
    for key in ("issueComments", "reviewComments"):
        for c in rec.get(key, []) or []:
            if not is_bot(c.get("author")):
                n += 1
    return n


langs = discover_langs(det)

# service -> lang -> {"autopr": int, "teams": int}
data = {}


def bump(service, lang, channel, amount):
    service = PERIOD_ALIAS.get(service, service)
    data.setdefault(service, {}).setdefault(lang, {"autopr": 0, "teams": 0})
    data[service][lang][channel] += amount


# Pass 1: AutoPR human comments. Also collect the known-service vocabulary from
# every AutoPR title so pass 2 can attribute freeform triage reasons to services.
known_services = set()
for lang in langs:
    created = {x["number"]: x.get("title") for x in load(os.path.join(det, lang, "github-prs-created.json"))}
    for title in created.values():
        s = service_from(title)
        if s:
            known_services.add(s)
    for rec in load(os.path.join(det, lang, "github-pr-comments.json")):
        n = human_comment_count(rec)
        if n <= 0:
            continue
        svc = service_from(created.get(rec["number"])) or UNATTRIBUTED
        bump(svc, lang, "autopr", n)

# Pass 2: Teams human replies, attributing triage reasons to services when possible.
for lang in langs:
    for t in load(os.path.join(det, lang, "teams-filtered.json")):
        if not t.get("kept"):
            continue
        n = t.get("humanReplyCount", 0) or 0
        if n <= 0:
            continue
        svc = service_from_reason(t.get("reason"), known_services) or UNATTRIBUTED
        bump(svc, lang, "teams", n)


def svc_total(svc):
    return sum(v["autopr"] + v["teams"] for v in data[svc].values())


# Real services ranked by total communication; the unattributed-triage bucket
# is kept aside so it is neither ranked among services nor folded into (others).
real = sorted((s for s in data if s != UNATTRIBUTED), key=lambda s: (-svc_total(s), s))

if TOP and len(real) > TOP:
    keep = real[:TOP]
    rest = real[TOP:]
    merged = {}
    for s in rest:
        for lang, v in data[s].items():
            merged.setdefault(lang, {"autopr": 0, "teams": 0})
            merged[lang]["autopr"] += v["autopr"]
            merged[lang]["teams"] += v["teams"]
    if merged:
        data["(others)"] = merged
        keep.append("(others)")
    real = keep

services = real + ([UNATTRIBUTED] if UNATTRIBUTED in data else [])

os.makedirs(res, exist_ok=True)
out_json = {
    "periodKey": periodKey,
    "languages": [DISPLAY_NAMES.get(l, l) for l in langs],
    "services": [
        {
            "service": s,
            "total": sum(v["autopr"] + v["teams"] for v in data[s].values()),
            "autoprTotal": sum(v["autopr"] for v in data[s].values()),
            "teamsTotal": sum(v["teams"] for v in data[s].values()),
            "byLanguage": {DISPLAY_NAMES.get(l, l): data[s][l] for l in langs if l in data[s]},
        }
        for s in services
    ],
}
json.dump(out_json, open(os.path.join(res, f"service-communication-{periodKey}.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)

# ---- grouped stacked bar chart ----
x = np.arange(len(services))
bw = 0.38
fig_w = max(12, len(services) * 0.85)
fig, ax = plt.subplots(figsize=(fig_w, 7))

for offset, channel, hatch in ((-bw / 2 - 0.02, "autopr", None), (bw / 2 + 0.02, "teams", "//")):
    bottoms = np.zeros(len(services))
    for lang in langs:
        vals = np.array([data[s].get(lang, {}).get(channel, 0) for s in services], dtype=float)
        if vals.sum() == 0:
            bottoms += vals
            continue
        ax.bar(x + offset, vals, bw, bottom=bottoms, color=COLORS.get(lang, "#888"),
               edgecolor="white", linewidth=0.4, hatch=hatch)
        bottoms += vals
    # total label on top of each bar
    for i, tot in enumerate(bottoms):
        if tot > 0:
            ax.text(x[i] + offset, tot + 0.3, str(int(tot)), ha="center", va="bottom", fontsize=7)

ax.set_xticks(x)
ax.set_xticklabels(services, rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Human communication count")
ax.set_title(f"AutoPR comments and Teams replies by service, stacked by language ({periodKey})\n"
             "Left bar = AutoPR human comments; right (hatched) bar = Teams human replies")

lang_handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS.get(l, "#888")) for l in langs]
lang_labels = [DISPLAY_NAMES.get(l, l) for l in langs]
ch_handles = [plt.Rectangle((0, 0), 1, 1, facecolor="#bbb"),
              plt.Rectangle((0, 0), 1, 1, facecolor="#bbb", hatch="//")]
leg1 = ax.legend(lang_handles, lang_labels, title="Language", loc="upper right")
ax.add_artist(leg1)
ax.legend(ch_handles, ["AutoPR comments", "Teams replies"], title="Channel", loc="upper right",
          bbox_to_anchor=(1.0, 0.72))

fig.tight_layout()
fig.savefig(os.path.join(res, f"service-communication-{periodKey}.png"), dpi=130)
plt.close(fig)

print("DONE", periodKey, "services:", len(services), "langs:", langs)
for s in services:
    print(f"  {s}: total={svc_total(s) if s in data else '-'} "
          f"autopr={sum(v['autopr'] for v in data[s].values())} "
          f"teams={sum(v['teams'] for v in data[s].values())}")
