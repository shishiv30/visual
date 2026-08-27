---
name: windows-qt-ui
description: >-
  Styles the Windows PySide6 pose client (QSS tokens, accent buttons, list
  cards, player overlay chrome). Use when changing clients/windows UI,
  QPushButton colors, list rows, capture/player layout, or theme.py.
---

# Windows Qt UI

Desktop client only. Use QSS and `QPalette`, not HTML/CSS frameworks.

## Tokens

Defined in `clients/windows/ui/theme.py`:

- Surface `#121212` (black window)
- Blue `#1E88E5` — Camera, Import
- Purple `#8E24AA` — Reanalyze
- Watermelon `#E94B6A` — Delete
- 6–10px radii, 32px control height
- `SPACE_CHAPTER` 36 — major sections (report chapters; player ↔ report)
- `SPACE_PANEL` 24 — sibling panels/cards in a section
- `SPACE_TEXT` 16 — stacked text paragraphs; text ↔ chart/image/report inside a panel
- Score rings: `score_purple(score)` dark → light purple by value
- Level trophy: green / blue / purple / gold by stage tier
- Terrain: diamond icons (no colored chip background); double black = two black diamonds

Accent controls: **colored fill, white icon and label** (background and text swapped vs. outline-on-white). Default buttons: dark fill, light label. Do not keep a light gray window.

Layout rhythm: never join paragraphs with `\n` in one `QLabel` — use separate widgets and layout spacing. Charts/images/reports stack full-width inside a panel (not beside text); sibling chart panels may still share a 2–3 column grid. Report chapter titles are gray 32px with 16px bottom gap and no numeric prefix.

## Patterns

- List rows are cards: rounded thumb, title / duration / status chip, actions on the right
- Player chrome floats on the video; do not steal a permanent strip that shrinks the picture
- Back / Play / Record / dialog OK·Cancel follow system or chrome text color, not accent blue/green/red
- Floating back (`make_floating_back` / `#floatingBack`) sits top-left on prepare, capture, and player; list has no back
- One stylesheet from `app_stylesheet()` on the `QApplication` or main window
- Pointer cursor: `PointerButtonFilter` in code. Qt Style Sheets do **not** support CSS `cursor`; it logs `Unknown property cursor`
- Display copy: always `t("English key")` from `locales/strings.json` (key is English; no `en` field; at least `zh`). Never hardcode UI/report prose.

## Do not

- Decorative gradients, random drop shadows, emoji as icons
- Per-page private color palettes
- WeChat / TikTok / YouTube SDKs (share opens public web URLs only)
