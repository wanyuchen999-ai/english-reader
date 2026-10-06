# -*- coding: utf-8 -*-
"""Merge downloaded word-list zips into worddata.js used by the reader page.

Output format (compact, loaded as a plain script, no CORS/file:// issues):
window.WORDDATA = { "word": [levelRank, "usphone", "pos. 释义"], ... }
A word keeps the LOWEST level rank it appears in (i.e. the stage where it is
first taught)."""
import json
import re
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE.parent / "worddata.js"

LEVELS = {  # rank by teaching stage
    "zk": 1, "gk": 2, "cet4": 3, "cet6": 4, "ky": 5,
    "ielts": 6, "toefl": 7, "gre": 8,
}
# 与 download.py 的 WANTED 保持一致：按正则在目录里找文件，避免手写文件名出错
PATTERNS = [
    (r"^\d+_PEPXiaoXue[3456]_[12]\.zip$", "zk"),
    (r"^\d+_PEPChuZhong[789]_1\.zip$", "zk"),
    (r"^\d+_ChuZhong_[23]\.zip$", "zk"),
    (r"^\d+_GaoZhong_[23]\.zip$", "gk"),
    (r"^\d+_CET4_[123]\.zip$", "cet4"),
    (r"^\d+_CET6_[123]\.zip$", "cet6"),
    (r"^\d+_KaoYan_[123]\.zip$", "ky"),
    (r"^\d+_IELTS_[23]\.zip$", "ielts"),
    (r"^\d+_TOEFL_[23]\.zip$", "toefl"),
    (r"^\d+_GRE_[23]\.zip$", "gre"),
]


def collect_files():
    files = {}
    for p in sorted(HERE.glob("*.zip")):
        for pat, level in PATTERNS:
            if re.match(pat, p.name):
                files.setdefault(level, []).append(p)
                break
    return files

WORD_RE = re.compile(r"^[a-z][a-z'·.-]*$")


def clean_trans(trans_list):
    parts = []
    for t in trans_list[:3]:
        pos = (t.get("pos") or "").strip()
        cn = (t.get("tranCn") or "").strip()
        if not cn:
            continue
        parts.append((pos + ". " + cn) if pos else cn)
    s = "；".join(parts)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:80]


def extract(zip_path, level):
    rank = LEVELS[level]
    words = {}
    with zipfile.ZipFile(zip_path) as z:
        name = z.namelist()[0]
        lines = z.read(name).decode("utf-8").splitlines()
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        head = (d.get("headWord") or "").strip()
        if not head:
            continue
        key = head.lower()
        if not WORD_RE.match(key):  # skip phrases / odd entries
            continue
        c = (d.get("content") or {}).get("word") or {}
        cc = c.get("content") or {}
        phone = (cc.get("usphone") or cc.get("phone") or cc.get("ukphone") or "").strip()
        tran = clean_trans(cc.get("trans") or [])
        if key in words:
            old = words[key]
            words[key] = [rank,
                          old[1] or phone,
                          old[2] or tran]
        else:
            words[key] = [rank, phone, tran]
    return words


def main():
    merged = {}   # key -> [rank, phone, trans, source_level]
    stats = {}
    FILES = collect_files()
    for level in LEVELS:
        files = FILES.get(level, [])
        total = 0
        for f in files:
            ws = extract(HERE / f, level)
            total += len(ws)
            for k, v in ws.items():
                cur = merged.get(k)
                if cur is None or v[0] < cur[0]:
                    merged[k] = [v[0], v[1], v[2], level]
                else:
                    # keep better phone/translation if missing
                    if not cur[1] and v[1]:
                        cur[1] = v[1]
                    if not cur[2] and v[2]:
                        cur[2] = v[2]
        stats[level] = total
    # count final distribution
    dist = {}
    for k, v in merged.items():
        dist[v[3]] = dist.get(v[3], 0) + 1
    print("raw per level:", stats)
    print("merged total:", len(merged))
    print("final distribution (word belongs to its earliest level):", dist)
    missing_tran = sum(1 for v in merged.values() if not v[2])
    print("entries without translation:", missing_tran)

    payload = {k: [v[0], v[1], v[2]] for k, v in sorted(merged.items())}
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    header = (
        "// 英语词库数据：单词 -> [等级(1初中 2高中 3四级 4六级 5考研 6雅思 7托福 8GRE), 美式音标, 中文释义]\n"
        "// 来源：kajweb/dict 公开词库（人教/四六级/考研/雅思/托福/GRE），本地使用，无需联网\n"
        "window.WORDDATA="
    )
    OUT.write_text(header + body + ";\n", encoding="utf-8")
    print("written:", OUT, OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
