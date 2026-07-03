"""Parse a saved Graph channel-message *delta* response into normalized
top-level threads, filtered to a reporting period by createdDateTime.

Usage: python parse_delta.py <saved-delta-output.txt> <periodStart> <periodEnd>
  dates as YYYY-MM-DD (inclusive). Prints one line per top-level thread and a
  JSON array (id, postAuthor, postTime, subject, createdInPeriod) to stdout tail.

The delta enumeration itself is done with the workiq MCP:
  workiq-fetch /teams/<team>/channels/<channel>/messages/delta
    ?$select=id,createdDateTime,lastModifiedDateTime,replyToId,subject,from
    &$filter=lastModifiedDateTime gt <periodStart>T00:00:00Z&$top=50
Only messages with replyToId=null are top-level thread starters.
"""
import sys, json, re

def extract_results(raw):
    i = raw.find("{")
    return json.JSONDecoder().raw_decode(raw[i:])[0].get("results", [])

def author_of(m):
    frm = m.get("from") or {}
    if frm.get("user"): return frm["user"].get("displayName", "?")
    if frm.get("application"): return frm["application"].get("displayName", "?")
    return "?"

def main():
    raw = open(sys.argv[1], encoding="utf-8").read()
    start, end = sys.argv[2], sys.argv[3]
    rows = []
    for r in extract_results(raw):
        d = r.get("data")
        if not d:
            continue
        for m in d.get("value", []):
            if m.get("replyToId"):
                continue  # skip replies; keep only thread starters
            created = m.get("createdDateTime", "")
            in_period = start <= created[:10] <= end
            rows.append({
                "threadId": m.get("id"),
                "postAuthor": author_of(m),
                "postTime": created,
                "subject": m.get("subject") or "",
                "createdInPeriod": in_period,
            })
    rows.sort(key=lambda x: x["postTime"])
    for x in rows:
        flag = "IN " if x["createdInPeriod"] else "out"
        print(f"{flag} {x['postTime'][:10]} {x['threadId']} | {x['postAuthor']} | {x['subject']!r}")
    injune = sum(1 for x in rows if x["createdInPeriod"])
    print(f"--- {len(rows)} threads, {injune} created in period ---")
    print(json.dumps([x for x in rows if x["createdInPeriod"]], ensure_ascii=False))

if __name__ == "__main__":
    main()
