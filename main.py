#!/usr/bin/env python3
"""Entrypoint for news-image-20261126 (fix pass 1).

What it does, in order:
  1. Checks build/front.html exists and passes the marker gate: a list of
     strings that must appear (edition date, hero banners, legend wording,
     DATE CHECK items, fix-pass-1 corrections) and a list that must never
     appear (wrong-edition dates, superseded fix-pass-1 wording,
     placeholder text).
  2. Self-checks the page structure: exactly 13 numbered map pins, one
     per hero/card story (01-13); 18 badge chips (13 story badges + 4
     legend chips + 1 CLAIM chip on the Hormuz inset); every card 04-13
     carries its story number beside its source kicker; the ALSO list
     holds 14 rows split 7 and 7 across two columns; the "ORIGINAL
     VECTOR ILLUSTRATIONS" note appears exactly once and sits in the map
     title, not over the ALSO columns.
  3. Verifies the repo-root entry.png byte by byte: PNG signature, IHDR
     exactly 1024x1024, 8-bit depth, palette colour type, CRC of every
     chunk, total size at most 1 MiB.
  4. Copies entry.png unchanged to $MAKEFUN_OUTPUT_DIR/entry.png
     (default /output/entry.png), writing with mode 0644, then re-reads
     the published copy and proves it is byte-identical (same SHA-256).

Standard library only. Deterministic: no timestamps, no randomness, so
two runs produce byte-identical output.
"""

import hashlib
import os
import struct
import sys
import zlib

REPO = os.path.dirname(os.path.abspath(__file__))
FRONT_HTML = os.path.join(REPO, "build", "front.html")
ENTRY_PNG = os.path.join(REPO, "entry.png")
MAX_BYTES = 1024 * 1024

MUST_APPEAR = [
    "26 NOVEMBER 2026",
    "THURSDAY",
    # Fix pass 1: hero 01 banner now names the Thursday follow-on
    # (Red Sea port strikes), not the Wednesday first claim.
    "RED SEA PORTS HIT",
    "first refinery claim Wed 25 Nov",
    "two tankers mined.",
    "IRREVERSIBLE",
    "13 DEAD, 13 TRAPPED",
    # Full legend wording — never the truncated "one side's" alone.
    "one side&rsquo;s claim",
    "DATE CHECK",
    "NOT YET:",
    "Spain votes Sun 29 Nov",
    "PINS 01&ndash;13",
    "27 STORIES",
    "12,000+",
    "3.25%",
    "&euro;1.7TN",
    "~$95",
    "13 + 13",
    "HOW SURE ARE WE?",
    "CONFIRMED 10 &middot; OFFICIAL 5 &middot; REPORTED 11 &middot; CLAIM 1",
    # Fix pass 1 corrections.
    "Australia Digital Duty of Care",
    "convicted of new charges",
    "Tariff hearing 25&nbsp;Jan&nbsp;2027",
    "15:00 LOCAL",
    "US STATE DEPT",
    # Fix pass 1: stat band second facts (research-only).
    "3 CRITICAL",
    "2ND-LARGEST OUTBREAK",
    "&euro;45BN FOR UKRAINE",
]

MUST_NOT_APPEAR = [
    "25 NOVEMBER 2026",   # wrong edition date
    "24 NOVEMBER 2026",   # wrong edition date
    "WEDNESDAY 25 NOVEMBER",
    "lorem",
    "TODO",
    "FIXME",
    "XXX",
    "SPDX-License-Identifier",
    "24 Nov 2026",
    "25 Nov 2026",
    # Superseded fix-pass-1 wording.
    "RAS TANURA HIT",                  # old hero 01 banner (Wed claim)
    "two tankers hit mines",           # old dek grammar
    "MORNING WEST JAVA RESCUE HALT",   # moved out of the UTC strip
    "Australia Duty of Care &mdash;",   # missing "Digital"
    "BRUSSELS &middot; 26&ndash;27 NOV",  # old #08 dateline kicker
    "tariff hearing 25 Jan.",          # old lowercase, yearless NOT YET
]


def fail(message):
    print("main.py: FAIL: " + message, file=sys.stderr)
    return 1


def check_front_html():
    if not os.path.isfile(FRONT_HTML):
        return fail("build/front.html is missing")
    with open(FRONT_HTML, "rb") as handle:
        text = handle.read().decode("utf-8")
    for marker in MUST_APPEAR:
        if marker not in text:
            return fail("front.html is missing required marker: %r" % marker)
    for marker in MUST_NOT_APPEAR:
        if marker in text:
            return fail("front.html contains forbidden marker: %r" % marker)
    # Self-check: the map must carry exactly 13 numbered pins, one per
    # hero/card story (01-13). Each pin is a red circle of radius 26.
    pins = text.count('r="26" fill="#b3231b" stroke="#f6f1e5"')
    if pins != 13:
        return fail("front.html has %d map pins, expected 13" % pins)
    # Self-check: every hero and card carries exactly one badge chip.
    # The legend holds one chip of each kind and the Hormuz inset holds
    # one CLAIM chip, so chips must number 13 + 4 + 1 = 18.
    chips = (text.count('chip cnf') + text.count('chip off')
             + text.count('chip rep') + text.count('chip clm'))
    if chips != 13 + 4 + 1:
        return fail("front.html has %d badge chips, expected 18 "
                    "(13 stories + 4 legend + 1 Hormuz inset)" % chips)
    # Self-check: every card 04-13 carries its story number beside its
    # source kicker, exactly once each.
    for number in ("04", "05", "06", "07", "08", "09", "10",
                   "11", "12", "13"):
        marker = '<span class="num">%s</span>' % number
        if text.count(marker) != 1:
            return fail("front.html has %d card-number spans for %s, "
                        "expected 1" % (text.count(marker), number))
    # Self-check: the ALSO list holds 14 rows, split 7 and 7 across two
    # columns, and the illustrations note sits in the map title only.
    also_start = text.index("ALSO ON THURSDAY")
    also_end = text.index("DATE CHECK", also_start)
    also_rows = text.count("<div><b>", also_start, also_end)
    if also_rows != 14:
        return fail("front.html ALSO section has %d rows, expected 14"
                    % also_rows)
    first_col = text.index('<div class="col">', also_start)
    second_col = text.index('<div class="col">', first_col + 1)
    col1_rows = text.count("<div><b>", first_col, second_col)
    col2_rows = text.count("<div><b>", second_col, also_end)
    if (col1_rows, col2_rows) != (7, 7):
        return fail("front.html ALSO columns hold %d and %d rows, "
                    "expected 7 and 7" % (col1_rows, col2_rows))
    if text.count("ORIGINAL VECTOR ILLUSTRATIONS") != 1:
        return fail("front.html has %d illustration notes, expected 1"
                    % text.count("ORIGINAL VECTOR ILLUSTRATIONS"))
    if text.index("ORIGINAL VECTOR ILLUSTRATIONS") > also_start:
        return fail("illustrations note sits after the ALSO title, "
                    "expected it in the map title")
    print("front.html: marker gate passed (%d required, %d forbidden); "
          "13 map pins, 13 story badges + 4 legend + 1 inset chips, "
          "card numbers 04-13 present, ALSO 7 + 7"
          % (len(MUST_APPEAR), len(MUST_NOT_APPEAR)))
    return 0


def check_png(data):
    if len(data) > MAX_BYTES:
        return fail("entry.png is %d bytes, over the 1 MiB limit" % len(data))
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return fail("entry.png does not start with the PNG signature")
    offset = 8
    seen_ihdr = False
    seen_iend = False
    while offset < len(data):
        if offset + 8 > len(data):
            return fail("entry.png is truncated inside a chunk header")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        ctype = data[offset + 4:offset + 8]
        end = offset + 8 + length + 4
        if end > len(data):
            return fail("entry.png is truncated inside chunk %r" % ctype)
        payload = data[offset + 8:offset + 8 + length]
        stored_crc = struct.unpack(">I", data[offset + 8 + length:end])[0]
        actual_crc = zlib.crc32(ctype + payload) & 0xFFFFFFFF
        if stored_crc != actual_crc:
            return fail("entry.png chunk %r has a bad CRC" % ctype)
        if ctype == b"IHDR":
            if seen_ihdr:
                return fail("entry.png has two IHDR chunks")
            seen_ihdr = True
            width, height, depth, colour = struct.unpack(">IIBB", payload[:10])
            if (width, height) != (1024, 1024):
                return fail("entry.png is %dx%d, expected 1024x1024"
                            % (width, height))
            if depth != 8:
                return fail("entry.png bit depth is %d, expected 8" % depth)
            if colour != 3:
                return fail("entry.png colour type is %d, expected 3 (palette)"
                            % colour)
        if ctype == b"PLTE":
            if length % 3 != 0 or length // 3 > 256:
                return fail("entry.png PLTE chunk holds %d colours, expected at most 256"
                            % (length // 3))
        if ctype == b"IEND":
            seen_iend = True
            if end != len(data):
                return fail("entry.png has trailing bytes after IEND")
        offset = end
    if not seen_ihdr:
        return fail("entry.png has no IHDR chunk")
    if not seen_iend:
        return fail("entry.png has no IEND chunk")
    print("entry.png: %d bytes, 1024x1024, 8-bit palette, all chunk CRCs OK"
          % len(data))
    return 0


def main():
    rc = check_front_html()
    if rc:
        return rc
    if not os.path.isfile(ENTRY_PNG):
        return fail("entry.png is missing from the repo root")
    with open(ENTRY_PNG, "rb") as handle:
        data = handle.read()
    rc = check_png(data)
    if rc:
        return rc
    digest = hashlib.sha256(data).hexdigest()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output/entry.png")
    out_path = out_dir if out_dir.endswith(".png") else os.path.join(out_dir, "entry.png")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    os.chmod(out_path, 0o644)
    with open(out_path, "rb") as handle:
        published = handle.read()
    if hashlib.sha256(published).hexdigest() != digest:
        return fail("published copy differs from the repo entry.png")
    if published != data:
        return fail("published copy is not byte-identical")
    print("published: %s sha256=%s mode=0644" % (out_path, digest))
    print("main.py: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
