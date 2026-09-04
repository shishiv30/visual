import json
from pathlib import Path

rows = json.loads(Path("tmp_i18n_keys.json").read_text(encoding="utf-8"))
lines = [f"{i}\t{r['en']}\t{r['zh']}" for i, r in enumerate(rows)]
Path("tmp_i18n_en_zh.tsv").write_text("\n".join(lines), encoding="utf-8")
print("tsv", len(lines))
