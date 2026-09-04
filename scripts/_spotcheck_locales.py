# -*- coding: utf-8 -*-
import json
from pathlib import Path

s = json.loads(Path("locales/strings.json").read_text(encoding="utf-8"))["strings"]
keys = [
    "Wedge christie",
    "hockey stop",
    "Mogul absorption",
    "Short-radius carve",
    "Parallel skiing",
    "Wedge glide",
    "Quiet upper body",
    "Sideslip and edge release",
    "Wedge mogul run",
    "Fall line",
    "Mogul fall-line",
]
out = []
for k in keys:
    if k not in s:
        out.append(f"MISSING {k}")
        continue
    out.append(f"=== {k}")
    for lang in ["zh", "fr", "de", "es", "it", "ja", "ko", "pt"]:
        out.append(f"  {lang}: {s[k].get(lang, '')}")
Path("locales/_ski_locale_fills/_spotcheck.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("wrote spotcheck")
