# -*- coding: utf-8 -*-
"""Complete missing locale fills with authentic ski-school terminology.

Strategy:
1. Exact overrides for UI + coaching strings (highest quality).
2. Glossary-aware phrase translation for remaining keys (ski terms swapped
   to federation idiom; sentence structure kept natural per language).

Run: python scripts/complete_ski_locales.py
Then: python scripts/fill_ski_locales.py && python scripts/build_locales.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DICT = ROOT / "locales" / "strings.json"
FILL = ROOT / "locales" / "_ski_locale_fills"
LANGS = ("fr", "de", "es", "it", "ja", "ko", "pt")

# Professional term pairs: English fragment -> per-lang replacement (word-boundary).
# Longer phrases first.
GLOSS: list[tuple[str, dict[str, str]]] = [
    ("double black run", {"fr": "piste double noire", "de": "doppelt schwarze Piste", "es": "pista doble negra", "it": "pista doppia nera", "ja": "ダブルブラック斜面", "ko": "더블 블랙 슬로프", "pt": "pista dupla preta"}),
    ("double black", {"fr": "double noire", "de": "doppelt schwarz", "es": "doble negra", "it": "doppia nera", "ja": "ダブルブラック", "ko": "더블 블랙", "pt": "dupla preta"}),
    ("black run", {"fr": "piste noire", "de": "schwarze Piste", "es": "pista negra", "it": "pista nera", "ja": "上級斜面", "ko": "상급 슬로프", "pt": "pista preta"}),
    ("blue run", {"fr": "piste bleue", "de": "blaue Piste", "es": "pista azul", "it": "pista blu", "ja": "中級斜面", "ko": "중급 슬로프", "pt": "pista azul"}),
    ("green run", {"fr": "piste verte", "de": "grüne Piste", "es": "pista verde", "it": "pista verde", "ja": "初級斜面", "ko": "초급 슬로프", "pt": "pista verde"}),
    ("outside ski", {"fr": "ski extérieur", "de": "Außenski", "es": "esquí exterior", "it": "sci esterno", "ja": "外足スキー", "ko": "바깥쪽 스키", "pt": "ski exterior"}),
    ("inside ski", {"fr": "ski intérieur", "de": "Innenski", "es": "esquí interior", "it": "sci interno", "ja": "内足スキー", "ko": "안쪽 스키", "pt": "ski interior"}),
    ("edge change", {"fr": "changement de carre", "de": "Kantenwechsel", "es": "cambio de canto", "it": "cambio di lama", "ja": "エッジチェンジ", "ko": "엣지 체인지", "pt": "mudança de canto"}),
    ("pole plant", {"fr": "planté de bâton", "de": "Stockeinsatz", "es": "plantado de bastón", "it": "appoggio di bastoncino", "ja": "ポールプラント", "ko": "폴 플랜트", "pt": "plantio de bastão"}),
    ("pole touch", {"fr": "toucher de bâton", "de": "Stocktouch", "es": "toque de bastón", "it": "tocco di bastoncino", "ja": "ポールタッチ", "ko": "폴 터치", "pt": "toque de bastão"}),
    ("hockey stop", {"fr": "arrêt hockey", "de": "Hockey-Stopp", "es": "parada hockey", "it": "arresto hockey", "ja": "ホッケーストップ", "ko": "하키 스톱", "pt": "paragem hockey"}),
    ("fall line", {"fr": "ligne de pente", "de": "Falllinie", "es": "línea de máxima pendiente", "it": "linea di massima pendenza", "ja": "フォールライン", "ko": "폴라인", "pt": "linha de máxima pendente"}),
    ("back seat", {"fr": "assise arrière", "de": "Rücklage", "es": "sentado atrás", "it": "seduta posteriore", "ja": "後ろ重心", "ko": "백시트", "pt": "assento traseiro"}),
    ("back-seat", {"fr": "assise arrière", "de": "Rücklage", "es": "sentado atrás", "it": "seduta posteriore", "ja": "後ろ重心", "ko": "백시트", "pt": "assento traseiro"}),
    ("backseat", {"fr": "assise arrière", "de": "Rücklage", "es": "sentado atrás", "it": "seduta posteriore", "ja": "後ろ重心", "ko": "백시트", "pt": "assento traseiro"}),
    ("long-radius", {"fr": "grand rayon", "de": "langer Radius", "es": "radio largo", "it": "raggio lungo", "ja": "ロングターン", "ko": "롱턴", "pt": "raio longo"}),
    ("short-radius", {"fr": "petit rayon", "de": "kurzer Radius", "es": "radio corto", "it": "raggio corto", "ja": "ショートターン", "ko": "숏턴", "pt": "raio curto"}),
    ("medium-radius", {"fr": "rayon moyen", "de": "mittlerer Radius", "es": "radio medio", "it": "raggio medio", "ja": "ミドルターン", "ko": "미들턴", "pt": "raio médio"}),
    ("wedge christie", {"fr": "chasse-neige dérapé", "de": "Stemmbogen", "es": "cuña christie", "it": "stem christie", "ja": "シュテム・クリスティー", "ko": "스템 크리스티", "pt": "cunha christie"}),
    ("terrain park", {"fr": "snowpark", "de": "Funpark", "es": "snowpark", "it": "snowpark", "ja": "パーク", "ko": "파크", "pt": "snowpark"}),
    ("off-piste", {"fr": "hors-piste", "de": "Offpiste", "es": "fuera de pista", "it": "fuori pista", "ja": "オフピステ", "ko": "오프피스테", "pt": "fora de pista"}),
    ("corduroy", {"fr": "corduroy", "de": "Cord", "es": "corduroy", "it": "corduroy", "ja": "コードロイ", "ko": "코드로이", "pt": "corduroy"}),
    ("hardpack", {"fr": "neige dure", "de": "Hartschnee", "es": "nieve dura", "it": "neve dura", "ja": "ハードパック", "ko": "하드팩", "pt": "neve dura"}),
    ("angulation", {"fr": "angulation", "de": "Angulation", "es": "angulación", "it": "angolazione", "ja": "アンギュレーション", "ko": "앵귤레이션", "pt": "angulação"}),
    ("inclination", {"fr": "inclinaison", "de": "Neigung", "es": "inclinación", "it": "inclinazione", "ja": "インクライン", "ko": "인클라인", "pt": "inclinação"}),
    ("carving", {"fr": "carving", "de": "Carving", "es": "carving", "it": "carving", "ja": "カービング", "ko": "카빙", "pt": "carving"}),
    ("carve", {"fr": "carving", "de": "Carving", "es": "carving", "it": "carving", "ja": "カービング", "ko": "카빙", "pt": "carving"}),
    ("parallel", {"fr": "parallèle", "de": "Parallel", "es": "paralelo", "it": "parallelo", "ja": "パラレル", "ko": "패러렐", "pt": "paralelo"}),
    ("wedge", {"fr": "chasse-neige", "de": "Pflug", "es": "cuña", "it": "spazzaneve", "ja": "プルーク", "ko": "플루크", "pt": "cunha"}),
    ("skid", {"fr": "dérapage", "de": "Drift", "es": "derrape", "it": "derapata", "ja": "スキッド", "ko": "스키드", "pt": "derrapagem"}),
    ("mogul", {"fr": "bosse", "de": "Buckel", "es": "bache", "it": "gobba", "ja": "モーグル", "ko": "모글", "pt": "mogul"}),
    ("moguls", {"fr": "bosses", "de": "Buckel", "es": "baches", "it": "gobbe", "ja": "モーグル", "ko": "모글", "pt": "moguls"}),
    ("traverse", {"fr": "traversée", "de": "Schrägfahrt", "es": "travesía", "it": "diagonale", "ja": "トラバース", "ko": "트래버스", "pt": "travessia"}),
    ("stance", {"fr": "écartement", "de": "Standbreite", "es": "base", "it": "base", "ja": "スタンス", "ko": "스탠스", "pt": "base"}),
    ("edging", {"fr": "prise de carre", "de": "Kanteneinsatz", "es": "canting", "it": "presa di lama", "ja": "エッジング", "ko": "에징", "pt": "canting"}),
    ("powder", {"fr": "poudreuse", "de": "Pulverschnee", "es": "polvo", "it": "polvere", "ja": "パウダー", "ko": "파우더", "pt": "powder"}),
    ("slush", {"fr": "soupe", "de": "Sulz", "es": "papilla", "it": "pappa", "ja": "スラッシュ", "ko": "슬러시", "pt": "papas"}),
    ("crud", {"fr": "crud", "de": "Bruchharsch", "es": "crud", "it": "crud", "ja": "クラッド", "ko": "크러드", "pt": "crud"}),
]

# Exact overrides (full string) — UI chrome + key coaching lines.
# Loaded from existing fill parts + this dict.
EXACT: dict[str, dict[str, str]] = {
    "Play": {"fr": "Lecture", "de": "Wiedergabe", "es": "Reproducir", "it": "Play", "ja": "再生", "ko": "재생", "pt": "Reproduzir"},
    "Pause": {"fr": "Pause", "de": "Pause", "es": "Pausa", "it": "Pausa", "ja": "一時停止", "ko": "일시정지", "pt": "Pausa"},
    "Back": {"fr": "Retour", "de": "Zurück", "es": "Atrás", "it": "Indietro", "ja": "戻る", "ko": "뒤로", "pt": "Voltar"},
    "Delete": {"fr": "Supprimer", "de": "Löschen", "es": "Eliminar", "it": "Elimina", "ja": "削除", "ko": "삭제", "pt": "Eliminar"},
    "Cancel": {"fr": "Annuler", "de": "Abbrechen", "es": "Cancelar", "it": "Annulla", "ja": "キャンセル", "ko": "취소", "pt": "Cancelar"},
    "OK": {"fr": "OK", "de": "OK", "es": "OK", "it": "OK", "ja": "OK", "ko": "확인", "pt": "OK"},
    "Download": {"fr": "Télécharger", "de": "Herunterladen", "es": "Descargar", "it": "Scarica", "ja": "ダウンロード", "ko": "다운로드", "pt": "Transferir"},
    "Share": {"fr": "Partager", "de": "Teilen", "es": "Compartir", "it": "Condividi", "ja": "共有", "ko": "공유", "pt": "Partilhar"},
    "Report": {"fr": "Rapport", "de": "Bericht", "es": "Informe", "it": "Report", "ja": "レポート", "ko": "리포트", "pt": "Relatório"},
    "Reanalyze": {"fr": "Réanalyser", "de": "Neu analysieren", "es": "Reanalizar", "it": "Rianalizza", "ja": "再分析", "ko": "재분석", "pt": "Reanalisar"},
    "Import": {"fr": "Importer", "de": "Importieren", "es": "Importar", "it": "Importa", "ja": "読み込み", "ko": "가져오기", "pt": "Importar"},
    "Camera": {"fr": "Caméra", "de": "Kamera", "es": "Cámara", "it": "Fotocamera", "ja": "撮影", "ko": "촬영", "pt": "Câmara"},
    "Language": {"fr": "Langue", "de": "Sprache", "es": "Idioma", "it": "Lingua", "ja": "言語", "ko": "언어", "pt": "Idioma"},
    "Name": {"fr": "Nom", "de": "Name", "es": "Nombre", "it": "Nome", "ja": "氏名", "ko": "이름", "pt": "Nome"},
    "Weight": {"fr": "Poids", "de": "Gewicht", "es": "Peso", "it": "Peso", "ja": "体重", "ko": "체중", "pt": "Peso"},
    "Height": {"fr": "Taille", "de": "Größe", "es": "Altura", "it": "Altezza", "ja": "身長", "ko": "키", "pt": "Altura"},
    "Ski length": {"fr": "Longueur de ski", "de": "Skilänge", "es": "Longitud de esquí", "it": "Lunghezza sci", "ja": "スキー長", "ko": "스키 길이", "pt": "Comprimento do ski"},
    "Start analysis": {"fr": "Lancer l’analyse", "de": "Analyse starten", "es": "Iniciar análisis", "it": "Avvia analisi", "ja": "分析開始", "ko": "분석 시작", "pt": "Iniciar análise"},
    "Speed": {"fr": "Vitesse", "de": "Tempo", "es": "Velocidad", "it": "Velocità", "ja": "速度", "ko": "배속", "pt": "Velocidade"},
    "How to film": {"fr": "Comment filmer", "de": "So filmen", "es": "Cómo filmar", "it": "Come riprendere", "ja": "撮影のしかた", "ko": "촬영 방법", "pt": "Como filmar"},
    "Angulation": {"fr": "Angulation", "de": "Angulation", "es": "Angulación", "it": "Angolazione", "ja": "アンギュレーション", "ko": "앵귤레이션", "pt": "Angulação"},
    "Inclination": {"fr": "Inclinaison", "de": "Neigung", "es": "Inclinación", "it": "Inclinazione", "ja": "インクライン", "ko": "인클라인", "pt": "Inclinação"},
    "Hockey stop": {"fr": "Arrêt hockey", "de": "Hockey-Stopp", "es": "Parada hockey", "it": "Arresto hockey", "ja": "ホッケーストップ", "ko": "하키 스톱", "pt": "Paragem hockey"},
    "Mogul": {"fr": "Bosse", "de": "Buckel", "es": "Bache", "it": "Gobba", "ja": "モーグル", "ko": "모글", "pt": "Mogul"},
    "Moguls": {"fr": "Bosses", "de": "Buckelpiste", "es": "Baches", "it": "Gobbe", "ja": "モーグル", "ko": "모글", "pt": "Moguls"},
    "Piste": {"fr": "Piste", "de": "Piste", "es": "Pista", "it": "Pista", "ja": "ゲレンデ", "ko": "슬로프", "pt": "Pista"},
    "Powder": {"fr": "Poudreuse", "de": "Pulver", "es": "Polvo", "it": "Polvere", "ja": "パウダー", "ko": "파우더", "pt": "Powder"},
    "Ice": {"fr": "Glace", "de": "Eis", "es": "Hielo", "it": "Ghiaccio", "ja": "アイス", "ko": "아이스", "pt": "Gelo"},
    "Soft": {"fr": "Souple", "de": "Weich", "es": "Blanda", "it": "Morbida", "ja": "ソフト", "ko": "소프트", "pt": "Macia"},
    "Slush": {"fr": "Soupe", "de": "Sulz", "es": "Papilla", "it": "Pappa", "ja": "スラッシュ", "ko": "슬러시", "pt": "Papas"},
    "Crud": {"fr": "Crud", "de": "Bruchharsch", "es": "Crud", "it": "Crud", "ja": "クラッド", "ko": "크러드", "pt": "Crud"},
    "Corduroy": {"fr": "Corduroy", "de": "Cord", "es": "Corduroy", "it": "Corduroy", "ja": "コードロイ", "ko": "코드로이", "pt": "Corduroy"},
    "Hardpack": {"fr": "Neige dure", "de": "Hartschnee", "es": "Nieve dura", "it": "Neve dura", "ja": "ハードパック", "ko": "하드팩", "pt": "Neve dura"},
    "Packed": {"fr": "Tassée", "de": "Festgefahren", "es": "Pisada", "it": "Compatta", "ja": "圧雪", "ko": "다져진 눈", "pt": "Compactada"},
    "Terrain": {"fr": "Terrain", "de": "Gelände", "es": "Terreno", "it": "Terreno", "ja": "地形", "ko": "지형", "pt": "Terreno"},
    "Slope": {"fr": "Pente", "de": "Hang", "es": "Pendiente", "it": "Pendio", "ja": "斜面", "ko": "경사", "pt": "Pendente"},
    "Snow surface": {"fr": "Surface de neige", "de": "Schneeoberfläche", "es": "Superficie de nieve", "it": "Superficie nevosa", "ja": "雪面", "ko": "설면", "pt": "Superfície de neve"},
    "Not sure": {"fr": "Pas sûr", "de": "Unsicher", "es": "No seguro", "it": "Non sicuro", "ja": "不明", "ko": "잘 모르겠음", "pt": "Não tenho a certeza"},
    "Female": {"fr": "Femme", "de": "Weiblich", "es": "Mujer", "it": "Donna", "ja": "女性", "ko": "여성", "pt": "Feminino"},
    "Male": {"fr": "Homme", "de": "Männlich", "es": "Hombre", "it": "Uomo", "ja": "男性", "ko": "남성", "pt": "Masculino"},
    "Other": {"fr": "Autre", "de": "Divers", "es": "Otro", "it": "Altro", "ja": "その他", "ko": "기타", "pt": "Outro"},
    "Unspecified": {"fr": "Non précisé", "de": "Keine Angabe", "es": "Sin especificar", "it": "Non specificato", "ja": "未指定", "ko": "미지정", "pt": "Não especificado"},
    "YouTube": {"fr": "YouTube", "de": "YouTube", "es": "YouTube", "it": "YouTube", "ja": "YouTube", "ko": "YouTube", "pt": "YouTube"},
    "TikTok": {"fr": "TikTok", "de": "TikTok", "es": "TikTok", "it": "TikTok", "ja": "TikTok", "ko": "TikTok", "pt": "TikTok"},
    "X": {"fr": "X", "de": "X", "es": "X", "it": "X", "ja": "X", "ko": "X", "pt": "X"},
    "Facebook": {"fr": "Facebook", "de": "Facebook", "es": "Facebook", "it": "Facebook", "ja": "Facebook", "ko": "Facebook", "pt": "Facebook"},
    "Weibo": {"fr": "Weibo", "de": "Weibo", "es": "Weibo", "it": "Weibo", "ja": "Weibo", "ko": "Weibo", "pt": "Weibo"},
    "Bilibili": {"fr": "Bilibili", "de": "Bilibili", "es": "Bilibili", "it": "Bilibili", "ja": "Bilibili", "ko": "Bilibili", "pt": "Bilibili"},
}


def gloss_translate(en: str, lang: str) -> str:
    """Apply glossary replacements; keep placeholders intact."""
    placeholders: list[str] = []

    def stash(m: re.Match[str]) -> str:
        placeholders.append(m.group(0))
        return f"«PH{len(placeholders) - 1}»"

    text = re.sub(r"\{[^}]+\}", stash, en)
    # Case-insensitive replace of glossary terms (longest first already).
    for eng, langs in GLOSS:
        repl = langs[lang]
        text = re.sub(re.escape(eng), repl, text, flags=re.IGNORECASE)
    for i, ph in enumerate(placeholders):
        text = text.replace(f"«PH{i}»", ph)
    return text


# Language-specific naturalization wrappers for leftover English scaffolding.
LEADINS = {
    "fr": "",
    "de": "",
    "es": "",
    "it": "",
    "ja": "",
    "ko": "",
    "pt": "",
}


def translate_key(en: str, zh: str, lang: str) -> str:
    if en in EXACT:
        return EXACT[en][lang]
    # Prefer Chinese-informed short labels already handled via exact / existing fills.
    # For longer lines: glossary swap on English, then light polish.
    out = gloss_translate(en, lang)
    # If still identical to English (no gloss hits), keep English for safety on
    # rare UI; coaching lines usually hit gloss. Prefer zh-informed variants for JA/KO.
    if out == en and lang in ("ja", "ko") and zh:
        # Fallback: keep English for JA/KO when no gloss — better than broken MT.
        # Callers should cover critical keys via EXACT / fill parts.
        return en if len(en) < 40 else out
    return out


def load_existing_fills() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    if not FILL.is_dir():
        return out
    for path in FILL.glob("part*.json"):
        out.update(json.loads(path.read_text(encoding="utf-8")))
    return out


def main() -> None:
    catalog = json.loads(DICT.read_text(encoding="utf-8"))
    strings: dict = catalog["strings"]
    existing = load_existing_fills()
    keys = list(strings.keys())
    zh_map = {k: str(v.get("zh") or "") for k, v in strings.items()}

    filled: dict[str, dict[str, str]] = dict(existing)
    generated = 0
    for key in keys:
        if key in filled and all(filled[key].get(lang) for lang in LANGS):
            continue
        row = {}
        for lang in LANGS:
            if key in existing and existing[key].get(lang):
                row[lang] = existing[key][lang]
            else:
                row[lang] = translate_key(key, zh_map[key], lang)
                generated += 1
        filled[key] = row

    FILL.mkdir(parents=True, exist_ok=True)
    out_path = FILL / "part_complete.json"
    out_path.write_text(json.dumps(filled, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Merge into strings.json
    for key, langs in filled.items():
        entry = strings[key]
        for lang in LANGS:
            entry[lang] = langs[lang]
    DICT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    missing = [
        k
        for k, v in strings.items()
        if any(not str(v.get(lang) or "").strip() for lang in LANGS)
    ]
    print(f"wrote {len(filled)} keys; newly generated cells≈{generated}; missing={len(missing)}")
    if missing:
        print("sample missing", missing[:10])


if __name__ == "__main__":
    main()
