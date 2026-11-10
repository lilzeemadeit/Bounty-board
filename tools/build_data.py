"""Build the compact card file the deck builder reads.

Input : punk-records/english/data/*.json + packs.json (official English card list, scraped)
Output: cards.json  — one record per gameplay card, with printings, effect tags and
        parsed leader conditions (used by the compatibility filter).
"""
import json, glob, re, sys, os, collections, html

SRC = sys.argv[1]          # .../punk-records/english
OUT = sys.argv[2]

packs = json.load(open(os.path.join(SRC, "packs.json")))
records = []
for f in sorted(glob.glob(os.path.join(SRC, "data", "*.json"))):
    records += json.load(open(f))

# Official ban list effective Oct 12, 2026 (en.onepiece-cardgame.com/news/restriction.html)
BANNED = ["OP06-047", "OP03-040", "OP06-086", "ST10-001", "OP06-116", "OP14-020"]
BANNED_PAIRS = [["OP07-115", "EB04-058"], ["OP11-040", "OP11-067"], ["OP11-040", "OP08-069"]]
# Bandai block-icon exceptions (en.onepiece-cardgame.com/news/blockicon-card.html)
STD_PERMITTED = ["EB01-006","EB02-061","EB03-061","EB04-044","EB05-014","OP01-016","OP01-120","OP02-013","OP03-122","OP04-083","OP05-069","OP05-074","OP05-119","OP06-118","OP06-119","OP07-051","OP08-118","OP09-004","OP09-051","OP09-093","OP09-118","OP09-119","OP10-119","OP11-118","OP12-118","OP13-118","OP13-119","OP13-120","OP14-119","OP15-118","OP16-063","OP16-065","OP16-073","OP17-005","OP17-022","OP17-062","OP17-112","OP17-118","EB04-061"]
STD_BLOCK4 = ["OP01-039","OP01-055","OP02-005","OP02-068","OP03-008","OP03-044","OP03-048","OP03-072","OP03-097","OP04-016","OP04-077","OP04-096","ST01-011","ST02-007","ST06-008"]

def pack_label(pid):
    p = packs.get(pid)
    if not p:
        return "?"
    lab = (p.get("title_parts") or {}).get("label") or ""
    if pid == "569901": return "Promo"
    if pid == "569801": return "Other"
    return lab or html.unescape(p["raw_title"])

def pack_name(pid):
    p = packs.get(pid)
    if not p: return ""
    t = (p.get("title_parts") or {}).get("title") or html.unescape(p["raw_title"])
    return html.unescape(t)

# ---------- effect tags ----------
TAGS = [
    ("rest",     "Rests opponent",   r"\b[Rr]est (?:up to |all |\d+ )?[^.]{0,80}?opponent's|opponent's [^.]{0,60}?(?:will not become active|cannot be set as active)"),
    ("ko",       "K.O.",             r"\bK\.O\. (?:up to|all|\d)"),
    ("bounce",   "Return to hand",   r"to the owner's hand"),
    ("bottom",   "Bottom of deck",   r"bottom of the owner's deck"),
    ("powdown",  "Reduce power",     r"[−-]\d+ power"),
    ("powup",    "Gain power",       r"\+\d+ power"),
    ("costdown", "Reduce cost",      r"[−-]\d+ cost"),
    ("draw",     "Draw",             r"\b[Dd]raw (?:up to )?\d+ cards?"),
    ("search",   "Look / search",    r"[Ll]ook at (?:up to )?\d+ cards? from the top of your deck"),
    ("donadd",   "Add DON!!",        r"[Aa]dd up to \d+ DON!! cards? from your DON!! deck|[Aa]dd \d+ DON!! cards? from your DON!! deck"),
    ("dongive",  "Give DON!!",       r"\b[Gg]ive [^.]{0,60}DON!!"),
    ("donminus", "DON!! −",          r"DON!! [−-]\d"),
    ("active",   "Set active",       r"[Ss]et [^.]{0,60}?as active"),
    ("life",     "Life cards",       r"\bLife\b"),
    ("play",     "Play from hand/trash/deck", r"[Pp]lay up to \d+[^.]{0,120}?from your (?:hand|trash|deck)"),
    ("trash",    "Uses trash",       r"from your trash"),
    ("discard",  "Opponent trashes", r"[Yy]our opponent trashes|[Tt]rash up to \d+ (?:card|of your opponent)"),
    ("noatk",    "Can't attack / block", r"cannot attack|cannot activate \[Blocker\]|cannot be blocked"),
    ("negate",   "Negate effects",   r"[Nn]egate the effect|without (?:its|their) effects?|loses? all effects"),
    ("protect",  "Protection",       r"cannot be K\.O\.'d|would be K\.O\.'d|would be removed from the field|cannot be removed"),
    ("rush",     "Rush",             r"\[Rush"),
    ("blocker",  "Blocker",          r"\[Blocker\]"),
    ("banish",   "Banish",           r"\[Banish\]"),
    ("double",   "Double Attack",    r"\[Double Attack\]"),
    ("unblock",  "Unblockable",      r"\[Unblockable\]"),
    ("onplay",   "On Play",          r"\[On Play\]"),
    ("onko",     "On K.O.",          r"\[On K\.O\.\]"),
    ("whenatk",  "When Attacking",   r"\[When Attacking\]"),
    ("actmain",  "Activate: Main",   r"\[Activate: ?Main\]"),
    ("counter_ev", "Counter event",  r"\[Counter\]"),
    ("onblock",  "On Block",         r"\[On Block\]"),
    ("oppattack","On opponent's attack", r"\[On Your Opponent's Attack\]"),
]
TAGRX = [(k, re.compile(rx)) for k, _, rx in TAGS]

# ---------- leader conditions ----------
SENT_SPLIT = re.compile(r"(?<=[.)])\s+(?=(?:\[|[A-Z]))")
COND_START = re.compile(r"(?:[Ii]f|\band) your Leader(?:'s)? (?=is |has |type |card name |colors )")
CUT = re.compile(r" and (?!the \{)")

def strip_reminder(s):
    return re.sub(r"\([^)]*\)", "", s)

def parse_cond(clause):
    """Return (alternatives, unknown_flag). alternatives: list of [kind, value]."""
    part = CUT.split(clause, 1)[0]
    alts = []
    if re.match(r"(?:card name includes)", part):
        for q in re.findall(r'"([^"]+)"', part): alts.append(["nameinc", q])
    elif re.match(r"type includes", part) or "type includes" in part:
        for q in re.findall(r'"([^"]+)"', part): alts.append(["typeinc", q])
    else:
        for t in re.findall(r"\{([^}]+)\}", part): alts.append(["type", t])
        if re.search(r"\bis\b", part):
            for n in re.findall(r"\[([^\]]+)\]", part): alts.append(["name", n])
    if "multicolored" in part: alts.append(["multi", 1])
    m = re.search(r"colors include (\w+)", part)
    if m: alts.append(["color", m.group(1).capitalize()])
    for a in re.findall(r"<(\w+)> attribute", part): alts.append(["attr", a])
    unknown = (not alts) and bool(re.search(r"[\[{\"<]", part))
    return alts, unknown

def segments(effect, trigger):
    segs = []
    prev_c = None
    for kind, text in (("e", effect), ("t", trigger)):
        if not text or text.strip() in ("-", ""):
            continue
        for s in SENT_SPLIT.split(text.strip()):
            s = s.strip()
            if not s: continue
            core = strip_reminder(re.sub(r"\[[^\]]*\]", "", s)).strip(" .:")
            seg = {"k": kind}
            if kind == "e" and len(core) < 3:
                seg["k"] = "kw"          # keyword-only line, e.g. "[Blocker]"
            if re.match(r"Under the rules of this game", s):
                seg["k"] = "rule"
            alts, unk, ctext = [], False, None
            for m in COND_START.finditer(s):
                clause = s[m.end():].split(",")[0].split(":")[0]
                a, u = parse_cond(clause)
                if a:
                    alts += a
                    ctext = (ctext + "; " if ctext else "") + ("If your Leader " + clause).strip()
                unk = unk or u
            if not alts and not unk and prev_c and re.match(r"Then,", s):
                seg["c"], seg["ct"] = prev_c  # "Then," follows the previous condition
            if alts:
                seg["c"], seg["ct"] = alts, ctext
                prev_c = (alts, ctext)
            elif not s.startswith("Then"):
                prev_c = None
            if unk: seg["u"] = 1
            if kind != "kw" or "c" in seg or "u" in seg:
                segs.append(seg)
            else:
                segs.append(seg)
    return segs

# ---------- group printings ----------
by_base = collections.OrderedDict()
for r in records:
    base = re.sub(r"_.*", "", r["id"])
    by_base.setdefault(base, []).append(r)

def sort_key(cid):
    m = re.match(r"([A-Z]+)(\d*)-(\d+)", cid)
    order = {"ST": 1, "OP": 0, "EB": 2, "PRB": 3, "P": 4}
    if not m: return (9, 0, 0)
    return (order.get(m.group(1), 5), int(m.group(2) or 0), int(m.group(3)))

out = []
for base in sorted(by_base, key=sort_key):
    prints = by_base[base]
    main = next((p for p in prints if p["id"] == base), prints[0])
    variants = []
    seen = set()
    for p in sorted(prints, key=lambda p: (p["id"] != base, p["id"])):
        if p["id"] in seen: continue
        seen.add(p["id"])
        variants.append([p["id"][len(base):], pack_label(p["pack_id"]), p["rarity"]])
    blocks = [p["block_number"] for p in prints if p["block_number"] is not None]
    eff = (main["effect"] or "").strip()
    if eff == "-": eff = ""
    trg = (main.get("trigger") or "").strip()
    text_all = eff + " " + trg
    tags = [k for k, rx in TAGRX if rx.search(text_all)]
    if trg: tags.append("trigger")
    if main["category"] == "Leader": tags = [t for t in tags]
    rules = re.findall(r"Under the rules of this game[^.]*\.", eff)
    rec = {
        "i": base,
        "n": main["name"],
        "c": main["category"][0],              # L C E S
        "co": main["colors"],
        "k": main["cost"],                     # leaders: life
        "p": main["power"],
        "ct": main["counter"],
        "a": (main["attributes"] or [None])[0],
        "t": main["types"],
        "e": eff,
        "tr": trg,
        "r": main["rarity"],
        "s": pack_label(main["pack_id"]),
        "sn": pack_name(main["pack_id"]),
        "b": max(blocks) if blocks else None,
        "v": variants,
        "g": tags,
        "sg": segments(eff, trg) if main["category"] != "Leader" else [],
    }
    if rules: rec["ru"] = rules
    if re.search(r"any number of this card", eff): rec["any"] = 1
    if base in BANNED: rec["ban"] = 1
    out.append(rec)

meta = {
    "updated": "2026-10-30",
    "through": "OP-17",
    "banned": BANNED,
    "pairs": BANNED_PAIRS,
    "stdPermitted": STD_PERMITTED,
    "stdBlock4": STD_BLOCK4,
    "tags": [[k, label] for k, label, _ in TAGS] + [["trigger", "Has Trigger"]],
    "sets": [],
}
seen = set()
for r in out:
    for v in r["v"]:
        if v[1] not in seen:
            seen.add(v[1])
def set_key(s):
    m = re.match(r"([A-Z]+)-?(\d+)", s)
    if not m: return (9, 0)
    return ({"OP": 0, "EB": 1, "PRB": 2, "ST": 3}.get(m.group(1), 5), int(m.group(2)))
meta["sets"] = sorted(seen, key=set_key)
json.dump({"meta": meta, "cards": out}, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))

# ---------- report ----------
cc = collections.Counter(r["c"] for r in out)
print("cards", len(out), dict(cc), "printings", sum(len(r["v"]) for r in out))
print("size KB", os.path.getsize(OUT) // 1024)
withc = [r for r in out if any("c" in s for s in r["sg"])]
unk = [r for r in out if any(s.get("u") for s in r["sg"])]
print("cards with leader conditions", len(withc), "uncertain", len(unk))
print("tag counts", collections.Counter(t for r in out for t in r["g"]).most_common())
print("rules", sum(1 for r in out if "ru" in r), "any-number", sum(1 for r in out if "any" in r))
