# Desktop ↔ Android feature parity (curriculum / report v3)

Windows PySide6 ([`clients/windows`](../../clients/windows)) is the **product source**. Android ([`clients/android`](../../clients/android)) must share the same content JSON and converge on the same assess/report semantics.

The older Chinese checklist [`mobile-parity-checklist.md`](mobile-parity-checklist.md) still describes the **five-chapter / curriculum v2** product surface. Prefer **this document** for content version, report chapters, and the gap matrix.

---

## 1. Desktop feature inventory

### Screens (4-page stack)

| Page | Role |
|------|------|
| **List** | Camera, Import, Language; clip cards (Pending / Processing / Done); Report / Reanalyze / Delete; **Possible stage** chip when classification is ambiguous |
| **Capture** | Live record or file import; trim if &gt; 120s; normalize ≤720p / 30fps / H.264 |
| **Prepare** | Person box seeds, logical in/out, athlete profile, **optional scene** (terrain / slope / snow), Start analysis |
| **Player** | Letterboxed media, COCO-17 overlay, filmstrip, chrome (play, locator, speed, like/unlike, bad skeleton, download, share), **12-chapter stage report** |

### Analysis pipeline (Python `core/sports`)

1. Pose → `analysis.json` (MediaPipe + `core_map`)
2. Turn segmentation (`turns.py`)
3. Metrics catalog (`metrics.py` + `knowledge/metrics.json`)
4. `classify_v3` + athlete / scene context
5. Gate scoring + skill tree + knowledge slice (`kb.v1.json`)
6. `stage_report.json` schema **3.0.0**

### Report chapters (12)

1. Summary  
2. Why this stage  
3. Core metrics  
4. Turn-by-turn  
5. Checkpoints  
6. Skill tree  
7–11 (collapsed by default): Stage tutorial, Drills, Faults and fixes, Terrain and venue, Equipment  
12. Filming and disclaimer  

Empty chapters are hidden (so a stored 2.1.0 report still renders what it can).

### Other desktop product features

- Athlete profiles + history for the skill tree  
- Correction dialog → `report_correction.json`  
- Frame feedback → `frame_feedback.json`  
- Scene hints from prior analysis (`scene_infer`)  
- Camera motion labels (static / panning / follow)  
- Overlay MP4 download (Android: JPEG still only)  

---

## 2. Shared content contract

Both clients must use these **repo files** (Android: Gradle copy into APK assets at build time; Windows: read live from the repo via `core`):

| Artifact | Path |
|----------|------|
| Curriculum | `content/ski/curriculum.v3.json` (`schema_version` **3.0.0**) |
| Metrics registry | `content/ski/knowledge/metrics.json` |
| Knowledge pack | `content/ski/knowledge/kb.v1.json` |
| Supporting knowledge | `content/ski/knowledge/signals.json`, `body.json`, `expert.json` |
| Locales | `locales/strings.json` |
| Pose model | `models/pose_landmarker_full.task` |

Do **not** ship `curriculum.v2.json` as the Android runtime curriculum. Keep v2 on disk only for reading old stored reports / comparison tests.

iOS still copies v2 via `scripts/generate_ios_xcodeproj.py` until an iOS v3 pass — that is an explicit follow-up, not Android scope.

---

## 3. Gap matrix

| Area | Desktop | Android (before this sync) | Target |
|------|---------|----------------------------|--------|
| Curriculum asset | v3 | v2 copy | Same v3 file |
| Knowledge assets | Yes | None | Bundle `knowledge/*` |
| Locales | `strings.json` | Same file | Keep |
| Assess | turns → metrics → classify_v3 | Kotlin `ClassifyV3` + `MetricPack` proxies; legacy ladder only as fallback | Same formulas; float tolerances OK |
| Report schema | 3.0.0 / 12 chapters | 3.0.0 full blocks (`tree`, `metrics`, `knowledge_ref`/`focus`, `filming`) | Match Windows chapter templates |
| Prepare scene | Terrain / slope / snow | Match desktop | Match desktop |
| Possible stage | List + report | Emit + show when ambiguous | Emit + show when ambiguous |
| Correction UI | Yes | Local `report_correction.json` | Local |
| Overlay download | MP4 | JPEG still | Deferred (honest JPEG) |
| Optical-flow camera motion | P1c | Heuristic/absent | Deferred |
| scene_infer hints | Prepare | Absent | Deferred |

---

## 4. Phased checklist

- [x] **Phase 0** — This document + README / checklist links  
- [x] **Phase 1** — Gradle copies `curriculum.v3.json` + `knowledge/*`; Kotlin loaders  
- [x] **Phase 2** — Prepare scene; StageReport 3.0 + 12-chapter panel; correction dialog  
- [x] **Phase 3** — Turns / metrics bridge / classify_v3-oriented assess; fixture tests  
- [x] **Phase 3b** — Report fidelity: full StageReport contract + Windows-matching chapter templates + branch skill tree  
- [ ] **Phase 4 (deferred)** — Overlay MP4, full camera_motion, scene_infer, iOS asset switch  

### Assess note

Android classify path is **`ClassifyV3`** (same weights/gates as desktop). The legacy signal ladder remains only as a fallback when the clip is unusable for scored candidates, and for unit regression of `Assess.classify`. Unmapped metrics stay **not measured** (never fake 0). Knowledge chapters resolve pack entities via `knowledge_ref` + `knowledge_focus` ids — tutorial prose is not embedded in the report.

Analyze speed (current): frames downscaled to long-edge ≤720 and sampled at ≤30fps before MediaPipe; loading overlay shows percent. Still deferred: MediaCodec sequential decode, cancel button, lite landmarker.

---

## 5. Build / verify

```powershell
cd d:\AI\visual
powershell -File scripts/build_android_apk.ps1
```

Unit tests under `clients/android/app/src/test` must load `content/ski/curriculum.v3.json` from the repo.

---

## References

- Design: [`docs/superpowers/specs/2026-08-30-ski-report-v3-design.md`](../superpowers/specs/2026-08-30-ski-report-v3-design.md)  
- Windows product (flows; chapter count may lag): [`docs/windows-product.md`](../windows-product.md)  
- Mobile UI checklist (v2-era chapters): [`mobile-parity-checklist.md`](mobile-parity-checklist.md)  
