import sys, json, re, html

def strip_html(s):
    if not s: return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def author_of(m):
    frm = m.get("from") or {}
    if frm.get("user"): return frm["user"].get("displayName", "?"), "human"
    if frm.get("application"): return frm["application"].get("displayName", "?"), "bot"
    return "?", "unknown"

def extract_results(raw):
    # find the JSON object after "MCP server 'workiq': " or plain
    i = raw.find("{")
    dec = json.JSONDecoder()
    obj, _ = dec.raw_decode(raw[i:])
    return obj.get("results", [])

def gh_links(text):
    return sorted(set(re.findall(r"https?://github\.com/[^\s\"'<>)\]]+", text)))

def main():
    raw = open(sys.argv[1], encoding="utf-8").read()
    results = extract_results(raw)
    for r in results:
        d = r.get("data")
        if not d:
            err = r.get("error", {})
            print(f"  ERROR: {json.dumps(err)[:120]}")
            continue
        # single message (has id) or a replies collection (has value)
        if "value" in d:
            vals = d["value"]
            # parent message id from @odata.context: .../messages('<id>')/replies
            ctx = d.get("@odata.context", "")
            mm = re.search(r"messages\('(\d+)'\)", ctx)
            pid = mm.group(1) if mm else "?"
            humans = 0; bots = 0
            for m in vals:
                _, kind = author_of(m)
                if kind == "human": humans += 1
                elif kind == "bot": bots += 1
            print(f"  REPLIES parent={pid} total={len(vals)} human={humans} bot={bots}")
        else:
            m = d
            author, kind = author_of(m)
            body = strip_html((m.get("body") or {}).get("content", ""))
            links = gh_links(body)
            print(f"ID {m.get('id')} | {author} ({kind}) | subj={m.get('subject')!r}")
            print(f"   body: {body[:400]}")
            if links: print(f"   GH: {links}")
        print()

if __name__ == "__main__":
    main()
