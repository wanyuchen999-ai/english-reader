# -*- coding: utf-8 -*-
"""Download selected word-list zips from kajweb/dict via the GitHub contents API
(raw.githubusercontent.com is unreachable on this network)."""
import json
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
WANTED = [
    (r"^\d+_PEPXiaoXue[3456]_[12]\.zip$", "zk"),   # 人教小学 3-6 年级，打底基础词
    (r"^\d+_PEPChuZhong[789]_1\.zip$", "zk"),       # 人教初中 7-9 年级
    (r"^\d+_ChuZhong_[23]\.zip$", "zk"),
    (r"^\d+_GaoZhong_[23]\.zip$", "gk"),
    (r"^\d+_CET4_[123]\.zip$", "cet4"),
    (r"^\d+_CET6_[123]\.zip$", "cet6"),
    (r"^\d+_KaoYan_[123]\.zip$", "ky"),
    (r"^\d+_IELTS_[23]\.zip$", "ielts"),
    (r"^\d+_TOEFL_[23]\.zip$", "toefl"),
    (r"^\d+_GRE_[23]\.zip$", "gre"),
]


def api(url):
    req = urllib.request.Request(url, headers={"User-Agent": "wordlist-downloader"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main():
    listing = json.loads(api("https://api.github.com/repos/kajweb/dict/contents/book"))
    targets = []
    for f in listing:
        for pat, level in WANTED:
            if re.match(pat, f["name"]):
                targets.append((f["name"], level, f["size"]))
                break
    print(f"{len(targets)} files to download")
    for name, level, size in targets:
        out = HERE / name
        if out.exists() and out.stat().st_size > 1000:
            print(f"skip (exists) {name}")
            continue
        url = f"https://api.github.com/repos/kajweb/dict/contents/book/{name}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "wordlist-downloader",
                          "Accept": "application/vnd.github.raw+json"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    data = r.read()
                out.write_bytes(data)
                print(f"ok {name} ({level}) {len(data)} bytes")
                break
            except Exception as e:
                print(f"retry {attempt + 1} {name}: {e}")
                time.sleep(2)
        time.sleep(0.3)
    # sanity check: every file is a valid zip
    bad = []
    for name, level, _ in targets:
        p = HERE / name
        if not p.exists():
            bad.append(name)
            continue
        try:
            with zipfile.ZipFile(p) as z:
                z.namelist()
        except Exception:
            bad.append(name)
    if bad:
        print("BAD/MISSING:", bad)
        sys.exit(1)
    print("all zips valid")


if __name__ == "__main__":
    main()
