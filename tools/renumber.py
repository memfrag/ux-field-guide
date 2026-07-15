#!/usr/bin/env python3
"""
renumber.py — deterministic chapter renumbering for the UX Field Manual.

WHY THIS EXISTS
----------------
Inserting a new chapter mid-document means every chapter after it shifts by
one (or more, if inserting several at once). Doing that by hand means finding
every sec-num div, every HTML section comment, every "class="n">NN.M<" entry
span, every "(NN.M)" prose cross-reference, every "ch. NN" / "Chapter NN" /
"NN ✕" mention, the nav dropdown, the five part-divider ranges, the README
table, and the cheat sheet — and getting every single one right, including
the ones that LOOK like a chapter reference but aren't (a screen-size "6.7″",
a contrast ratio "7.5:1", a CSS "scale(1.05)"). A hand pass on 2026-07-16
caught nine straggler bugs after the "automated" regex pass. This script
makes the mechanical part deterministic and self-verifying so that doesn't
happen again.

HOW A CHAPTER'S "LABEL" WORKS
------------------------------
Existing chapters are labeled by their current numeric sec-num ("16", "07").
A chapter you are INSERTING should be labeled with a placeholder token of the
form "NEW-<section-id>" (e.g. "NEW-grid") wherever its number would otherwise
go — the sec-num div, the HTML comment, and every entry span prefix
("NEW-grid.1", "NEW-grid.2", ...). Cross-references TO a new chapter (from
anywhere in the document, including forward-references written before the
new chapter exists) also use the placeholder: "(ch. NEW-grid)" or
"(NEW-grid.3)". The appendix section keeps the literal label "A" and is
never renumbered.

WORKFLOW
--------
1. Insert new <section id="...">...</section> blocks at the correct
   position in the document (i.e. document order = final chapter order).
   Use the NEW-<id> placeholder token everywhere that section's chapter
   number would appear. Do NOT touch the nav ToC, part-divider ranges, or
   any cross-references elsewhere in the document by hand — the script
   handles those.
2. Run `renumber.py check index.html` — a dry run. It prints the computed
   old/placeholder → final-number mapping, regenerates nothing, and flags
   any bare "(NN)" parenthetical it finds (these are inherently ambiguous —
   could be a chapter ref, could be a footnote, a percentage, anything — so
   they are never auto-applied, only reported for manual fix-up before you
   run apply).
3. Fix anything `check` flagged, by hand, using the printed mapping.
4. Run `renumber.py apply index.html --readme README.md --cheatsheet
   cheatsheet.html`. This rewrites index.html in place (sec-nums, comments,
   entry spans, decimal cross-refs, "ch./chapter NN[–MM]" refs, "NN ✕"
   refs, the nav ToC, the five part-divider ranges), regenerates the
   README's chapter table, and propagates safe prose-ref fixes into the
   cheat sheet. It then re-parses its own output and runs the full
   verification suite; if anything fails, it refuses to leave the files
   changed and prints the failure instead.

WHAT COUNTS AS A "SAFE" PATTERN TO AUTO-SHIFT
-----------------------------------------------
Only patterns that cannot plausibly mean anything else:
  - class="n">NN.M<                    (entry span definitions)
  - (NN.M) / NN.M) / NN.M,  etc.        (decimal cross-refs in prose)
  - ch. NN  /  ch. NN–MM                (case-insensitive "ch.")
  - chapter NN  /  Chapter NN           (case-insensitive "chapter")
  - NN ✕                                (anti-pattern callouts)
  - <div class="sec-num">NN</div>
  - <!-- ============ NN TITLE ============ -->
Decimal refs are excluded when immediately followed by a quote, inch mark,
colon, or percent sign — these are the real false positives found in this
document (screen sizes in inches, WCAG contrast ratios). All of this is
scoped to TEXT NODES only (never inside a tag's attributes) and the
<style> block is treated as fully opaque, so CSS numbers are never at risk.

Bare "(NN)" integers are NEVER auto-shifted — only reported. Going forward,
write cross-references as "ch. NN" or a decimal entry ref, never a bare
"(NN)"; `check` will flag any bare parenthetical integer still in the
document as a reminder of this convention.
"""

import argparse
import json
import re
import sys
from pathlib import Path

STYLE_TOKEN = "\x00STYLE_BLOCK\x00"
NEW_PREFIX = "NEW-"


# ---------------------------------------------------------------- parsing --

def isolate_style(html):
    m = re.search(r"<style>.*?</style>", html, re.S)
    if not m:
        return html, ""
    return html[: m.start()] + STYLE_TOKEN + html[m.end():], m.group(0)


def restore_style(html, style_content):
    return html.replace(STYLE_TOKEN, style_content)


def read_sections(html):
    """Return sections in document order: id, current label, full title,
    and toc_title (the short form for the nav dropdown, if the <h2> carries
    a data-toc="..." override — e.g. <h2 data-toc="Nielsen's Ten">Nielsen's
    Ten, Condensed</h2> — otherwise the full title is reused)."""
    pat = re.compile(
        r'<section id="([a-z0-9]+)">\s*<div class="sec-head reveal">\s*'
        r'<div class="sec-num">([A-Za-z0-9-]+)</div>\s*'
        r'<h2(?:\s+data-toc="([^"]*)")?>(.*?)</h2>',
        re.S,
    )
    out = []
    for m in pat.finditer(html):
        title = m.group(4).strip()
        toc_title = m.group(3).strip() if m.group(3) else title
        out.append({"id": m.group(1), "label": m.group(2), "title": title, "toc_title": toc_title})
    return out


def read_parts(html):
    """Return part dividers in document order with the section id each
    one immediately precedes (used to attribute chapters to parts), plus
    each part's tagline (the descriptive text before the "· ch. NN–MM"
    range in its <p>, e.g. "How people perceive, decide, and touch")."""
    div_pat = re.compile(
        r'<div class="part" id="(part-\d+)">.*?<h2>([^<]+)</h2>\s*<p>(.*?)</p>', re.S
    )
    sec_pat = re.compile(r'<section id="([a-z0-9]+)">')
    markers = [(m.start(), "part", m.group(1), m.group(2), m.group(3)) for m in div_pat.finditer(html)]
    markers += [(m.start(), "section", m.group(1), None, None) for m in sec_pat.finditer(html)]
    markers.sort(key=lambda x: x[0])

    parts, current = [], None
    for _, kind, ident, name, tagline_raw in markers:
        if kind == "part":
            tagline = re.sub(r'\s*·\s*ch\.\s*\d+(–\d+)?\s*$', '', tagline_raw or '').strip()
            current = {"id": ident, "name": name, "tagline": tagline, "section_ids": []}
            parts.append(current)
        elif current is not None:
            current["section_ids"].append(ident)
    return parts


# ------------------------------------------------------------- numbering --

def build_mapping(sections):
    """Sequential numbering by document order. Appendix (label == 'A')
    is pinned last and excluded from the sequence. Returns:
      mapping: {old_label(str) -> new_number(int)}
      appendix_ids: set of section ids treated as the appendix
    """
    mapping = {}
    n = 0
    for s in sections:
        if s["label"] == "A":
            continue
        n += 1
        mapping[s["label"]] = n
    return mapping


def zpad(n):
    return f"{n:02d}"


# --------------------------------------------------------- safe rewriting --

def make_shifter(mapping):
    """old label (numeric string or 'NEW-id') -> new number, or None if
    the label isn't in the mapping (leave it alone — likely unrelated).

    Mapping keys are the label exactly as it appears in each section's
    sec-num div, which is always zero-padded ("02", "16"). References
    found in prose are NOT zero-padded ("2.1" not "02.1", "Chapter 8" not
    "Chapter 08") — so every lookup tries the exact string first, then a
    zero-padded 2-digit form, before giving up."""

    def shift(label):
        if label in mapping:
            return mapping[label]
        if label.isdigit():
            padded = label.zfill(2)
            if padded in mapping:
                return mapping[padded]
        return None

    return shift


def apply_safe_shifts(html, mapping):
    """Apply every unambiguous, auto-safe pattern. Returns (new_html, stats)."""
    shift = make_shifter(mapping)
    stats = {"decimal": 0, "ch_dot": 0, "chapter_word": 0, "cross_mark": 0,
             "sec_num": 0, "comment": 0, "unresolved": []}

    html, style_content = isolate_style(html)

    # decimal chapter.entry refs: numeric OR placeholder prefix, anywhere
    # in text nodes (entry spans, prose, JS comments alike).
    # chapter numbers are 1-31, never a leading zero as a standalone number
    # (that would false-positive on things like JS's "threshold: 0.08").
    decimal_pat = re.compile(
        r'\b(' + re.escape(NEW_PREFIX) + r'[a-z0-9]+|[1-9]\d?)\.(\d{1,2})\b(?!["″:%])'
    )

    def shift_in_text(text):
        def dec_repl(m):
            new = shift(m.group(1))
            if new is None:
                stats["unresolved"].append(f"decimal ref '{m.group(0)}' has no mapping")
                return m.group(0)
            stats["decimal"] += 1
            return f"{new}.{m.group(2)}"
        return decimal_pat.sub(dec_repl, text)

    parts = re.split(r"(<[^>]+>)", html)
    parts = [seg if seg.startswith("<") else shift_in_text(seg) for seg in parts]
    html = "".join(parts)

    # "ch. NN[–MM]" and "chapter NN" — case-insensitive, numeric or placeholder.
    # Both exclude a trailing ".digit" (e.g. the "Chapter 8.5" stylistic
    # phrasing that means entry 8.5) — that continuation belongs to the
    # decimal pass above; without this guard the two passes fight over the
    # same text and the second one double-shifts an already-shifted number.
    label_alt = r'(?:' + re.escape(NEW_PREFIX) + r'[a-z0-9]+|\d+)'
    no_decimal_tail = r'(?!\.\d)'

    def ch_dot_repl(m):
        lead = m.group(1)
        a = shift(m.group(2))
        if a is None:
            stats["unresolved"].append(f"'{m.group(0)}' has no mapping")
            return m.group(0)
        if m.group(3):
            b = shift(m.group(3))
            if b is None:
                stats["unresolved"].append(f"'{m.group(0)}' (range end) has no mapping")
                return m.group(0)
            stats["ch_dot"] += 1
            return f"{lead}. {zpad(a)}–{zpad(b)}"
        stats["ch_dot"] += 1
        return f"{lead}. {zpad(a)}"

    # the trailing \b is load-bearing: without it, a greedy digit match that
    # fails the no_decimal_tail lookahead can backtrack to a SHORTER digit
    # sequence that spuriously satisfies it (e.g. "ch. NEW-mapping.2" backs
    # off to "ch. NEW-mappin", or "ch. 10.2" backs off to "ch. 1", leaving
    # "0.2" as literal trailing text — producing "ch. 010.2"). Mid-number is
    # not a word boundary, so \b blocks exactly that spurious backtrack.
    html = re.sub(
        rf'([Cc]h)\. ({label_alt}){no_decimal_tail}\b(?:–({label_alt}))?',
        ch_dot_repl, html,
    )

    def chapter_repl(m):
        new = shift(m.group(2))
        if new is None:
            stats["unresolved"].append(f"'{m.group(0)}' has no mapping")
            return m.group(0)
        stats["chapter_word"] += 1
        # zero-padded to match "ch. NN" and the page's sec-num badges
        # ("01".."37" everywhere) — a bare "Chapter 8" reads inconsistent
        # right next to those.
        return f"{m.group(1)} {zpad(new)}"

    html = re.sub(
        rf'\b([Cc]hapter) ({label_alt}){no_decimal_tail}\b',
        chapter_repl, html,
    )

    # "NN ✕" / "NEW-id ✕"
    def cross_repl(m):
        new = shift(m.group(1))
        if new is None:
            stats["unresolved"].append(f"'{m.group(0)}' has no mapping")
            return m.group(0)
        stats["cross_mark"] += 1
        return f"{new} ✕"

    html = re.sub(rf'\b({label_alt}) ✕', cross_repl, html)

    # sec-num divs — "A" (the appendix) is pinned and never shifted.
    def secnum_repl(m):
        label = m.group(1)
        if label == "A":
            return m.group(0)
        new = shift(label)
        if new is None:
            stats["unresolved"].append(f"sec-num '{label}' has no mapping")
            return m.group(0)
        stats["sec_num"] += 1
        return f'<div class="sec-num">{zpad(new)}</div>'

    html = re.sub(r'<div class="sec-num">([A-Za-z0-9-]+)</div>', secnum_repl, html)

    # HTML section comments — charset must allow hyphens (this was the bug
    # that silently dropped 3 comments in the 2026-07-16 hand renumbering).
    def comment_repl(m):
        new = shift(m.group(1))
        if new is None:
            stats["unresolved"].append(f"comment '{m.group(0)}' has no mapping")
            return m.group(0)
        stats["comment"] += 1
        return f'<!-- ============ {new} {m.group(2)} ============ -->'

    html = re.sub(
        rf'<!-- ============ ({label_alt}) ([^=]+?) ============ -->',
        comment_repl, html,
    )

    html = restore_style(html, style_content)
    return html, stats


def find_bare_parens(html):
    """Report (never auto-fix) bare integer parentheticals like '(11)' —
    ambiguous, could be a stale chapter ref or something unrelated."""
    _, style_content = isolate_style(html)
    body = html.replace(style_content, "")
    hits = []
    for seg in re.split(r"(<[^>]+>)", body):
        if seg.startswith("<"):
            continue
        for m in re.finditer(r"\((\d{1,2})\)", seg):
            ctx = seg[max(0, m.start() - 50): m.end() + 15].replace("\n", " ")
            hits.append((m.group(1), ctx.strip()))
    return hits


# ------------------------------------------------------------ regenerate --

PART_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]


def regenerate_toc(html, sections, mapping, parts):
    id_to_new = {}
    id_to_toc_title = {}
    for s in sections:
        new = mapping.get(s["label"])
        id_to_new[s["id"]] = "A" if s["label"] == "A" else zpad(new)
        id_to_toc_title[s["id"]] = s["toc_title"]

    # Only parts that actually contain a numbered (non-appendix) chapter get
    # a roman numeral and a "Part N — Name" label; the appendix's trailing
    # part bucket (see read_parts) keeps its bare name, matching how the
    # appendix has always rendered with no part divider of its own.
    # first line has no leading indent: the regex match starts exactly at
    # "<ol", so whatever indentation precedes it in the original document
    # is preserved automatically and must not be duplicated here.
    lines = ['<ol class="toc-grid">']
    roman_i = 0
    for part in parts:
        has_numbered = any(id_to_new.get(sid, "A") != "A" for sid in part["section_ids"])
        if has_numbered:
            roman_i += 1
            label = f"Part {PART_ROMAN[roman_i - 1]} — {part['name']}"
        else:
            label = part["name"]
        lines.append(f'      <li class="part-head">{label}</li>')
        for sid in part["section_ids"]:
            if sid not in id_to_new:
                continue
            lines.append(
                f'      <li><a href="#{sid}"><b>{id_to_new[sid]}</b>{id_to_toc_title[sid]}</a></li>'
            )
    lines.append("    </ol>")
    new_block = "\n".join(lines)

    return re.sub(
        r'<ol class="toc-grid">.*?</ol>', lambda _: new_block, html, count=1, flags=re.S
    )


def regenerate_part_ranges(html, sections, mapping, parts):
    id_to_new = {s["id"]: mapping.get(s["label"]) for s in sections if s["label"] != "A"}
    for part in parts:
        nums = [id_to_new[sid] for sid in part["section_ids"] if sid in id_to_new]
        if not nums:
            continue
        lo, hi = min(nums), max(nums)
        # Replace the range within this specific part's <p>...ch. NN–MM</p>
        pat = re.compile(
            rf'(<div class="part" id="{part["id"]}">.*?<p>.*?ch\. )\d+–\d+(</p>)', re.S
        )
        html = pat.sub(lambda m: f"{m.group(1)}{zpad(lo)}–{zpad(hi)}{m.group(2)}", html, count=1)
    return html


def regenerate_readme_table(readme_text, sections, mapping, parts):
    # the README's title column mirrors the ToC's SHORT title (toc_title),
    # not the full <h2> — that's what the existing description lookup below
    # is keyed against, and what a human skimming the table expects.
    id_to_title = {s["id"]: s["toc_title"] for s in sections}
    id_to_new = {s["id"]: ("A" if s["label"] == "A" else zpad(mapping.get(s["label"])))
                 for s in sections}

    # pull existing descriptions (third column) keyed by section id from the
    # CURRENT readme table so hand-written blurbs survive regeneration.
    desc_by_title = {}
    for m in re.finditer(r'\|\s*[0-9A]+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', readme_text):
        desc_by_title[m.group(1).strip()] = m.group(2).strip()

    def strip_tags(s):
        return re.sub(r"<[^>]+>", "", s).replace("&amp;", "&")

    blocks = []
    roman_i = 0
    for part in parts:
        has_numbered = any(id_to_new.get(sid, "A") != "A" for sid in part["section_ids"])
        if has_numbered:
            roman_i += 1
            heading = f'**Part {PART_ROMAN[roman_i - 1]} — {part["name"]}**'
            if part["tagline"]:
                heading += f' · {part["tagline"]}'
        else:
            heading = f'**{part["name"]}**'
        blocks.append(f'{heading}\n')
        blocks.append("| # | Chapter | |")
        blocks.append("|---|---------|---|")
        for sid in part["section_ids"]:
            if sid not in id_to_title:
                continue
            title = strip_tags(id_to_title[sid])
            desc = desc_by_title.get(title, "*(describe this chapter)*")
            blocks.append(f"| {id_to_new[sid]} | {title} | {desc} |")
        blocks.append("")
    new_table = "\n".join(blocks).rstrip() + "\n"

    return re.sub(
        r"(## What's inside\n\n).*?(\nGrounded in)",
        lambda m: m.group(1) + new_table + m.group(2),
        readme_text, count=1, flags=re.S,
    )


# -------------------------------------------------------------- verify --

def verify(html):
    problems = []
    if html.count("<section") != html.count("</section"):
        problems.append("unbalanced <section> tags")
    if html.count("<div") != html.count("</div"):
        problems.append("unbalanced <div> tags")
    if html.count("<svg") != html.count("</svg"):
        problems.append("unbalanced <svg> tags")

    secnums = re.findall(r'<div class="sec-num">(\d+|A)</div>', html)
    numeric = [int(n) for n in secnums if n != "A"]
    if numeric != list(range(1, len(numeric) + 1)):
        problems.append(f"sec-num sequence not 1..N: {secnums}")
    if secnums and secnums[-1] != "A":
        problems.append("appendix 'A' is not last")

    secs = re.split(r'<section id="', html)[1:]
    all_entries = set()
    for s in secs:
        sid = s.split('"')[0]
        m = re.search(r'<div class="sec-num">(\d+|A)</div>', s)
        if not m:
            continue
        ch = m.group(1)
        nums = []
        for prefix, num in re.findall(r'class="n">([A-Za-z0-9]+)\.(\d+)<', s):
            key = f"{prefix}.{num}"
            if prefix.lstrip("0") != ch.lstrip("0") and prefix != ch:
                problems.append(f"{sid}(ch{ch}): entry {key} chapter mismatch")
            if key in all_entries:
                problems.append(f"duplicate entry {key} (in {sid})")
            all_entries.add(key)
            nums.append(int(num))
        if nums != list(range(1, len(nums) + 1)):
            problems.append(f"{sid}(ch{ch}): entries not sequential: {nums}")

    ids = set(re.findall(r'<section id="([a-z0-9]+)"', html))
    toc_m = re.search(r'class="toc-grid">.*?</ol>', html, re.S)
    if toc_m:
        toc_hrefs = re.findall(r'href="#([a-z0-9]+)"', toc_m.group(0))
        missing = [h for h in toc_hrefs if h not in ids]
        if missing:
            problems.append(f"ToC links to missing sections: {missing}")
        if len(toc_hrefs) != len(ids):
            problems.append(f"ToC has {len(toc_hrefs)} entries, doc has {len(ids)} sections")

    _, style_content = isolate_style(html)
    body = html.replace(style_content, "")
    prose_refs = set()
    for seg in re.split(r"(<[^>]+>)", body):
        if seg.startswith("<"):
            continue
        for m in re.finditer(r"\((\d{1,2}\.\d{1,2})[,\s\)’]", seg):
            prose_refs.add(m.group(1))
    dangling = sorted(r for r in prose_refs if r not in all_entries)
    if dangling:
        problems.append(f"prose refs pointing at nonexistent entries: {dangling}")

    return problems


# ------------------------------------------------------------------ CLI --

def cmd_check(args):
    html = Path(args.file).read_text(encoding="utf-8")
    sections = read_sections(html)
    mapping = build_mapping(sections)

    print(f"Sections found: {len(sections)} (document order)\n")
    print(f"{'ID':<16}{'LABEL':<12}{'NEW':<6}TITLE")
    for s in sections:
        new = "A" if s["label"] == "A" else zpad(mapping[s["label"]])
        flag = "  <- NEW" if s["label"].startswith(NEW_PREFIX) else ""
        print(f"{s['id']:<16}{s['label']:<12}{new:<6}{s['title']}{flag}")

    bare = find_bare_parens(html)
    print(f"\nBare '(NN)' parentheticals found: {len(bare)} "
          f"(never auto-fixed — review each before running apply)")
    for num, ctx in bare:
        print(f"  ({num})  ...{ctx}...")

    problems = verify(html)
    print(f"\nCurrent-file structural check: {'OK' if not problems else 'ISSUES FOUND'}")
    for p in problems:
        print(f"  - {p}")

    Path(args.dump_mapping).write_text(json.dumps(mapping, indent=2)) if args.dump_mapping else None
    if args.dump_mapping:
        print(f"\nMapping written to {args.dump_mapping}")


def cmd_apply(args):
    path = Path(args.file)
    html = path.read_text(encoding="utf-8")
    sections = read_sections(html)
    mapping = build_mapping(sections)
    parts = read_parts(html)

    new_html, stats = apply_safe_shifts(html, mapping)
    if stats["unresolved"]:
        print("REFUSING TO WRITE — unresolved references found:")
        for u in stats["unresolved"]:
            print(f"  - {u}")
        sys.exit(1)

    new_html = regenerate_toc(new_html, sections, mapping, parts)
    new_html = regenerate_part_ranges(new_html, sections, mapping, parts)

    problems = verify(new_html)
    if problems:
        review_path = path.with_suffix(".renumbered-review.html")
        review_path.write_text(new_html, encoding="utf-8")
        print(f"VERIFICATION FAILED — original file left untouched.")
        print(f"Output written for inspection to {review_path}")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    path.write_text(new_html, encoding="utf-8")
    print(f"{path}: renumbered and verified clean.")
    print(f"  decimal refs shifted:   {stats['decimal']}")
    print(f"  'ch./chapter' refs:     {stats['ch_dot'] + stats['chapter_word']}")
    print(f"  anti-pattern ✕ refs:    {stats['cross_mark']}")
    print(f"  sec-num divs:           {stats['sec_num']}")
    print(f"  section comments:       {stats['comment']}")

    bare = find_bare_parens(new_html)
    if bare:
        print(f"\nReminder: {len(bare)} bare '(NN)' parentheticals remain — "
              f"these were NOT touched (ambiguous). Review by hand:")
        for num, ctx in bare:
            print(f"  ({num})  ...{ctx}...")

    if args.readme:
        readme_path = Path(args.readme)
        readme_text = readme_path.read_text(encoding="utf-8")
        readme_text, rstats = apply_safe_shifts(readme_text, mapping)
        readme_text = regenerate_readme_table(readme_text, sections, mapping, parts)
        readme_path.write_text(readme_text, encoding="utf-8")
        print(f"\n{readme_path}: table regenerated, "
              f"{rstats['decimal'] + rstats['ch_dot'] + rstats['chapter_word']} prose refs shifted.")

    if args.cheatsheet:
        cs_path = Path(args.cheatsheet)
        cs_text = cs_path.read_text(encoding="utf-8")
        cs_text, cstats = apply_safe_shifts(cs_text, mapping)
        cs_path.write_text(cs_text, encoding="utf-8")
        print(f"{cs_path}: {cstats['decimal'] + cstats['ch_dot'] + cstats['chapter_word']} "
              f"prose refs shifted (title/structure NOT auto-updated — hand-authored).")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    pc = sub.add_parser("check", help="Dry run: show the mapping, flag bare-paren refs, verify current state.")
    pc.add_argument("file")
    pc.add_argument("--dump-mapping", help="Write the computed mapping to this JSON file.")
    pc.set_defaults(func=cmd_check)

    pa = sub.add_parser("apply", help="Renumber in place, regenerate ToC/parts, verify, and propagate to companion files.")
    pa.add_argument("file")
    pa.add_argument("--readme", help="Also regenerate this README's chapter table.")
    pa.add_argument("--cheatsheet", help="Also propagate safe prose-ref shifts into this file.")
    pa.set_defaults(func=cmd_apply)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
