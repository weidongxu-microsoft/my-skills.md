#!/usr/bin/env python3
"""Stage 2 helper: apply Teams relevance decisions to produce teams-filtered.json.

For each language under <metric-root>/details/<lang>/ this reads:
  - teams-raw.json      : authoritative delta thread list (from Stage 1)
  - teams-decisions.json: operator's Stage 2 relevance decisions, a JSON object
                          mapping threadId -> {"reason": str,
                                               "replyCount": int,       # total incl. bot
                                               "humanReplyCount": int}  # non-bot only

and writes teams-filtered.json: every in-period thread with a `kept` flag; retained
threads also carry reason / replyCount / humanReplyCount / replyCountCapped so Stage 3
can compute related-post counts and average replies and trace threads back to raw data.

Only threads with createdInPeriod == True are eligible to be kept, so threads that were
merely active-but-created-earlier (surfaced by delta) never inflate the created-in-period
count.

Usage:
    python build_teams_filtered.py <metric-root> [lang1 lang2 ...]

If no languages are given, every immediate subfolder of <metric-root>/details that
contains a teams-raw.json is processed. A language is skipped (with a warning) when it
has no teams-decisions.json, so you can run it incrementally as you classify channels.
"""
import json
import os
import sys

REPLY_PAGE_CAP = 50  # Graph channel-message /replies page size cap used in Stage 1.


def load_threads(raw):
    return raw["threads"] if isinstance(raw, dict) else raw


def process_language(det, lang):
    ldir = os.path.join(det, lang)
    raw_path = os.path.join(ldir, "teams-raw.json")
    dec_path = os.path.join(ldir, "teams-decisions.json")
    if not os.path.exists(raw_path):
        print(f"{lang}: no teams-raw.json, skipping")
        return None
    if not os.path.exists(dec_path):
        print(f"{lang}: no teams-decisions.json, skipping (write decisions first)")
        return None

    threads = load_threads(json.load(open(raw_path, encoding="utf-8")))
    decisions = json.load(open(dec_path, encoding="utf-8"))

    out = []
    for t in threads:
        tid = str(t.get("threadId") or t.get("id") or "")
        rec = {
            "threadId": tid,
            "postAuthor": t.get("postAuthor"),
            "postTime": t.get("postTime"),
            "subject": t.get("subject"),
            "createdInPeriod": t.get("createdInPeriod", False),
            "kept": False,
        }
        if tid in decisions and t.get("createdInPeriod", False):
            d = decisions[tid]
            total = int(d.get("replyCount", 0) or 0)
            human = int(d.get("humanReplyCount", 0) or 0)
            rec["kept"] = True
            rec["reason"] = d.get("reason", "")
            rec["replyCount"] = total
            rec["humanReplyCount"] = human
            rec["replyCountCapped"] = total >= REPLY_PAGE_CAP
        out.append(rec)

    json.dump(out, open(os.path.join(ldir, "teams-filtered.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    kept = [r for r in out if r["kept"]]
    avg_human = round(sum(r["humanReplyCount"] for r in kept) / len(kept), 2) if kept else 0
    print(f"{lang}: {len(kept)} kept / {len(out)} threads; avg human replies = {avg_human}")
    return len(kept)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    root = sys.argv[1]
    det = os.path.join(root, "details")
    langs = sys.argv[2:]
    if not langs:
        langs = sorted(
            d for d in os.listdir(det)
            if os.path.isfile(os.path.join(det, d, "teams-raw.json"))
        )
    for lang in langs:
        process_language(det, lang)
    print("DONE")


if __name__ == "__main__":
    main()
