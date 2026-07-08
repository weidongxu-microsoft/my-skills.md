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

# Optionally exclude one or more language keys (e.g. --exclude net). Output
# files then get a "_without_<keys>" suffix so they sit alongside the full report.
# "net" is accepted as an alias for the "dotnet" folder key.
EXCLUDE_ALIASES = {"net": "dotnet"}
EXCLUDE_TOKENS = []   # as typed by the user, used for the filename suffix
EXCLUDE_LANGS = []    # resolved to actual language folder keys
SUFFIX = ""
if "--exclude" in sys.argv:
    EXCLUDE_TOKENS = [x.strip() for x in sys.argv[sys.argv.index("--exclude") + 1].split(",") if x.strip()]
    EXCLUDE_LANGS = [EXCLUDE_ALIASES.get(x, x) for x in EXCLUDE_TOKENS]
    SUFFIX = "_without_" + "_".join(EXCLUDE_TOKENS)

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

# --- shared "SDK release support" channel (not language-specific) ---
# Threads here are release-time help requests; some name a service already charted
# this period (-> a 3rd release-support bar on that service), many name a service
# with no in-period AutoPR/Teams activity or are general tooling/process (-> the
# concise unattributed summary, kept out of the per-service bars).
# Service names as they appear in release-support bodies -> canonical token (aligned
# with the tokens the AutoPR/Teams passes already produce). "computevalidation" is the
# brand name for the Microsoft.Validate RP, mapped to the report's microsoftvalidate.
REL_KEYWORDS = {
    "securityinsights": "securityinsights",
    "cognitiveservices": "cognitiveservices",
    "computevalidation": "microsoftvalidate",
    "microsoftvalidate": "microsoftvalidate",
    "managednetworkfabric": "managednetworkfabric",
    "computebulkactions": "computebulkactions",
    "horizondb": "horizondb",
    "healthbot": "healthbot",
    "mysqlflexibleservers": "mysqlflexibleservers",
}


def service_from_release_support(body, known):
    """Attribute a release-support thread body to a service, or None (-> tooling)."""
    svc = service_from(body)  # explicit [AutoPR <lib>]
    if svc:
        return svc
    low = re.sub(r"[^a-z0-9]", "", (body or "").lower())
    cand = dict(REL_KEYWORDS)
    for tok in known:
        cand.setdefault(tok, tok)
    best = None
    for kw, canon in cand.items():
        if len(kw) >= 6 and kw in low and (best is None or len(kw) > best[0]):
            best = (len(kw), canon)
    return best[1] if best else None


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
    present = [d for d in os.listdir(details_dir)
               if os.path.isdir(os.path.join(details_dir, d)) and d != "sdk-release-support"]
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


langs = [l for l in discover_langs(det) if l not in EXCLUDE_LANGS]

# service -> lang -> {"autopr": int, "teams": int}
data = {}
# service -> int  (release-support human replies; not language-specific)
relsupport_data = {}


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


# Pass 3: shared "SDK release support" channel (not language-specific). Split the
# threads into two groups against the services that already exist in the chart from
# AutoPR + per-language Teams (the period-anchored "group_by_service" vocabulary):
#   - found    -> a service already charted this period: add as a 3rd release-support
#                 bar for that service (relsupport_data).
#   - not found -> either a service with no AutoPR/Teams activity in the period (e.g.
#                 a release happening long before/after generation) or general
#                 release tooling/process: collected for a concise report section.
# This keeps out-of-period releases and platform-tooling out of the per-service bars,
# where they cannot be time-aligned with the created-in-period cohort.
charted_services = set(data.keys())  # services from AutoPR (pass 1) + Teams (pass 2)
release_support_unattributed = []
_rel_path = os.path.join(det, "sdk-release-support", "teams-raw.json")
if os.path.exists(_rel_path):
    rel_vocab = set(charted_services)
    for t in load(_rel_path):
        if not t.get("createdInPeriod", True):
            continue
        n = t.get("humanReplyCount", 0) or 0
        if n <= 0:
            continue
        text = (t.get("subject") or "") + " " + (t.get("body") or "")
        svc = service_from_release_support(text, rel_vocab)
        if svc:
            svc = PERIOD_ALIAS.get(svc, svc)
        if svc and svc in charted_services:
            relsupport_data[svc] = relsupport_data.get(svc, 0) + n
        else:
            release_support_unattributed.append({
                "threadId": t.get("threadId"),
                "subject": (t.get("subject") or "").strip() or "(no subject)",
                "humanReplyCount": n,
                "resolvedService": svc,  # a service, but not charted this period, or None
                "category": "named-service-not-in-period-cohort" if svc else "tooling/process",
            })


def svc_total(svc):
    return sum(v["autopr"] + v["teams"] for v in data[svc].values()) + relsupport_data.get(svc, 0)


# Real services ranked by total communication; the unattributed-triage and the
# release-support-tooling buckets are kept aside so they are neither ranked among
# services nor folded into (others).
SPECIAL = {UNATTRIBUTED}
real = sorted((s for s in data if s not in SPECIAL), key=lambda s: (-svc_total(s), s))

if TOP and len(real) > TOP:
    keep = real[:TOP]
    rest = real[TOP:]
    merged = {}
    merged_rel = 0
    for s in rest:
        for lang, v in data[s].items():
            merged.setdefault(lang, {"autopr": 0, "teams": 0})
            merged[lang]["autopr"] += v["autopr"]
            merged[lang]["teams"] += v["teams"]
        merged_rel += relsupport_data.get(s, 0)
    if merged or merged_rel:
        data["(others)"] = merged
        if merged_rel:
            relsupport_data["(others)"] = merged_rel
        keep.append("(others)")
    real = keep

services = real + [s for s in (UNATTRIBUTED,) if s in data]

os.makedirs(res, exist_ok=True)
out_json = {
    "periodKey": periodKey,
    "languages": [DISPLAY_NAMES.get(l, l) for l in langs],
    "services": [
        {
            "service": s,
            "total": svc_total(s),
            "autoprTotal": sum(v["autopr"] for v in data[s].values()),
            "teamsTotal": sum(v["teams"] for v in data[s].values()),
            "releaseSupportTotal": relsupport_data.get(s, 0),
            "byLanguage": {DISPLAY_NAMES.get(l, l): data[s][l] for l in langs if l in data[s]},
        }
        for s in services
    ],
}
json.dump(out_json, open(os.path.join(res, f"service-communication-{periodKey}{SUFFIX}.json"), "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)

# ---- release-support threads that could NOT be tied to a charted service ----
# These are release/tooling efforts that don't time-align with the created-in-period
# cohort; summarize them in a small report section instead of forcing a bar.
if release_support_unattributed:
    ru = sorted(release_support_unattributed, key=lambda r: -r["humanReplyCount"])
    by_cat = {}
    for r in ru:
        by_cat.setdefault(r["category"], {"threads": 0, "humanReplies": 0})
        by_cat[r["category"]]["threads"] += 1
        by_cat[r["category"]]["humanReplies"] += r["humanReplyCount"]
    ru_json = {
        "periodKey": periodKey,
        "note": "SDK release-support threads not attributable to a service charted "
                "this period; kept out of the per-service bars (release/tooling effort "
                "is time-decoupled from the created-in-period AutoPR cohort).",
        "totalThreads": len(ru),
        "totalHumanReplies": sum(r["humanReplyCount"] for r in ru),
        "byCategory": by_cat,
        "threads": ru,
    }
    json.dump(ru_json, open(os.path.join(res, f"release-support-unattributed-{periodKey}{SUFFIX}.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

# ---- grouped stacked bar chart ----
have_rel = any(relsupport_data.get(s, 0) for s in services)
REL_COLOR = "#319795"  # teal, distinct from the language palette
x = np.arange(len(services))
bw = 0.27 if have_rel else 0.38
fig_w = max(12, len(services) * (1.0 if have_rel else 0.85))
fig, ax = plt.subplots(figsize=(fig_w, 7))

if have_rel:
    autopr_off, teams_off, rel_off = -(bw + 0.03), 0.0, (bw + 0.03)
else:
    autopr_off, teams_off, rel_off = -bw / 2 - 0.02, bw / 2 + 0.02, None

for offset, channel, hatch in ((autopr_off, "autopr", None), (teams_off, "teams", "//")):
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

if have_rel:
    rel_vals = np.array([relsupport_data.get(s, 0) for s in services], dtype=float)
    ax.bar(x + rel_off, rel_vals, bw, color=REL_COLOR, edgecolor="white",
           linewidth=0.4, hatch="xx")
    for i, tot in enumerate(rel_vals):
        if tot > 0:
            ax.text(x[i] + rel_off, tot + 0.3, str(int(tot)), ha="center", va="bottom", fontsize=7)

ax.set_xticks(x)
ax.set_xticklabels(services, rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Human communication count")
_channels_line = ("Left = AutoPR comments; middle (hatched //) = per-language Teams replies; "
                  "right (teal xx) = SDK release-support replies") if have_rel else \
                 "Left bar = AutoPR human comments; right (hatched) bar = Teams human replies"
ax.set_title(f"AutoPR comments and Teams replies by service, stacked by language ({periodKey})"
             + (f" — excluding {', '.join(DISPLAY_NAMES.get(l, l) for l in EXCLUDE_LANGS)}" if EXCLUDE_LANGS else "")
             + "\n" + _channels_line)

lang_handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS.get(l, "#888")) for l in langs]
lang_labels = [DISPLAY_NAMES.get(l, l) for l in langs]
ch_handles = [plt.Rectangle((0, 0), 1, 1, facecolor="#bbb"),
              plt.Rectangle((0, 0), 1, 1, facecolor="#bbb", hatch="//")]
ch_labels = ["AutoPR comments", "Teams replies"]
if have_rel:
    ch_handles.append(plt.Rectangle((0, 0), 1, 1, facecolor=REL_COLOR, hatch="xx"))
    ch_labels.append("Release-support replies")
leg1 = ax.legend(lang_handles, lang_labels, title="Language", loc="upper right")
ax.add_artist(leg1)
ax.legend(ch_handles, ch_labels, title="Channel", loc="upper right",
          bbox_to_anchor=(1.0, 0.72))

fig.tight_layout()
fig.savefig(os.path.join(res, f"service-communication-{periodKey}{SUFFIX}.png"), dpi=130)
plt.close(fig)

print("DONE", periodKey, "services:", len(services), "langs:", langs)
for s in services:
    print(f"  {s}: total={svc_total(s) if s in data else '-'} "
          f"autopr={sum(v['autopr'] for v in data[s].values())} "
          f"teams={sum(v['teams'] for v in data[s].values())} "
          f"relsupport={relsupport_data.get(s, 0)}")
if release_support_unattributed:
    ru = release_support_unattributed
    print("release-support UNATTRIBUTED: %d threads, %d human replies"
          % (len(ru), sum(r["humanReplyCount"] for r in ru)))
    for r in sorted(ru, key=lambda r: -r["humanReplyCount"]):
        print(f"    [{r['category']}] h={r['humanReplyCount']} svc={r['resolvedService']} :: {r['subject'][:70]}")
