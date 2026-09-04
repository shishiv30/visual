# -*- coding: utf-8 -*-
"""Remaining ski locale translations (professional coach register).

Compact tuples: (en, fr, de, es, it, ja, ko, pt)
"""
from __future__ import annotations

ROWS: list[tuple[str, str, str, str, str, str, str, str]] = []

def add(*cols: str) -> None:
    assert len(cols) == 8, cols[0] if cols else "?"
    ROWS.append(cols)  # type: ignore[arg-type]


# --- batch 1 ---
add("Flatten both skis to slip sideways, then edge again to stop — neither a locked edge nor a free slide.",
    "Mettez les deux skis à plat pour glisser de côté, puis remettez les carres pour vous arrêter — ni carre bloquée ni glissade libre.",
    "Beide Ski flach stellen und seitlich gleiten, dann wieder kanten und stoppen — weder blockierte Kante noch freies Rutschen.",
    "Pon ambos esquís planos para deslizar de lado y vuelve a cantar para parar: ni canto bloqueado ni desliz libre.",
    "Metti entrambi gli sci piatti per scivolare di lato, poi riprendi le lame e fermati — né lama bloccata né scivolata libera.",
    "両スキーをフラットにして横へ滑らせ、再エッジで止める——ロックしたエッジでも暴走スライドでもない。",
    "양 스키를 평평히 해 옆으로 미끄러진 뒤 다시 엣지를 세워 멈추세요 — 잠긴 엣지도, 통제 없는 슬라이드도 아님.",
    "Ponha ambos os skis planos para escorregar de lado e volte a cantar para parar — nem canto bloqueado nem deslize livre.")
add("Flex and extend to surface the skis",
    "Fléchissez et étendez pour faire remonter les skis",
    "Beugen und strecken, damit die Ski aufschwimmen",
    "Flexiona y extiende para hacer flotar los esquís",
    "Fletti ed estendi per far affiorare gli sci",
    "蹲伸でスキーを浮かせる",
    "굴신으로 스키를 띄우기",
    "Flexione e estenda para fazer os skis emergir")
add("Flex for rhythm", "Fléchir pour le rythme", "Beugen für den Rhythmus", "Flexión para el ritmo", "Flessione per il ritmo", "リズムのための屈曲", "리듬을 위한 굴곡", "Flexão para o ritmo")
add("Flex into the turn", "Fléchir dans le virage", "In den Schwung beugen", "Flexionar hacia la curva", "Flettere nella curva", "ターンへ入りながら屈曲", "턴 진입 굴곡", "Flexionar na curva")
add("Flex-and-extend rhythm", "Rythme flexion–extension", "Beuge-Streck-Rhythmus", "Ritmo flexión–extensión", "Ritmo flessione–estensione", "蹲伸リズム", "굴신 리듬", "Ritmo flexão–extensão")
add("Follow", "Suivi", "Follow", "Seguimiento", "Follow", "フォロー", "팔로우", "Seguir")
add("Follow camera", "Caméra en suivi", "Follow-Kamera", "Cámara en seguimiento", "Camera a seguire", "フォローカメラ", "팔로우 카메라", "Câmara a seguir")
add("Follow-cam; one alpine skier in frame.",
    "Caméra en suivi ; un seul skieur alpin dans le cadre.",
    "Follow-Cam; ein alpiner Skifahrer im Bild.",
    "Cámara en seguimiento; un solo esquiador alpino en cuadro.",
    "Camera a seguire; un solo sciatore alpino in campo.",
    "フォロー撮影。画面にはアルペンスキーヤー1人。",
    "팔로우 촬영. 화면에 알파인 스키어 한 명.",
    "Câmara a seguir; um único esquiador alpino no enquadramento.")
add("For your profile", "Pour votre profil", "Für Ihr Profil", "Para tu perfil", "Per il tuo profilo", "あなたのプロフィール向け", "내 프로필 기준", "Para o seu perfil")
add("Format", "Format", "Format", "Formato", "Formato", "形式", "형식", "Formato")
add("Four posture scores are coach heuristics (0–100), not lab biomechanics; they are not true speed, meter turn radius, or peak ski pressure.",
    "Les quatre scores de posture sont des heuristiques de coach (0–100), pas de la biomécanique de labo ; ce ne sont ni une vraie vitesse, ni un rayon en mètres, ni une pression de ski de pointe.",
    "Vier Haltungswerte sind Coach-Heuristiken (0–100), keine Labor-Biomechanik; keine echte Geschwindigkeit, kein Meter-Radius, kein Peak-Skidruck.",
    "Las cuatro puntuaciones de postura son heurísticas de coach (0–100), no biomecánica de laboratorio; no son velocidad real, radio en metros ni presión máxima de esquí.",
    "I quattro punteggi di postura sono euristiche da coach (0–100), non biomeccanica da laboratorio; non sono velocità vera, raggio in metri né pressione di picco.",
    "姿勢の4得点はコーチ経験則（0–100）であり実験室の生体力学ではありません。実速度・メートル半径・板底ピーク圧ではありません。",
    "자세 4점수는 코치 휴리스틱(0–100)이며 실험실 생체역학이 아닙니다. 실제 속도·미터 반경·스키 피크 압력이 아닙니다.",
    "As quatro pontuações de postura são heurísticas de coach (0–100), não biomecânica de laboratório; não são velocidade real, raio em metros nem pressão de pico.")
add("Frame locator JSON copied", "JSON du localisateur d’image copié", "Frame-Locator-JSON kopiert", "JSON del localizador de fotograma copiado", "JSON localizzatore frame copiato", "フレーム位置JSONをコピーしました", "프레임 위치 JSON 복사됨", "JSON do localizador de fotograma copiado")
add("From a gentle traverse, pivot both skis across the hill and set the edges to a stop.",
    "Depuis une traversée douce, pivotez les deux skis à travers la pente et posez les carres jusqu’à l’arrêt.",
    "Aus einer leichten Schrägfahrt beide Ski quer zum Hang drehen und kanten bis zum Stopp.",
    "Desde una travesía suave, pivota ambos esquís a través de la pendiente y planta cantos hasta parar.",
    "Da una diagonale dolce, pivota entrambi gli sci attraverso il pendio e metti le lame fino all’arresto.",
    "緩い斜滑降から両スキーを斜面横断にピボットし、エッジを立てて停止。",
    "완만한 트래버스에서 양 스키를 사면 가로로 피벗한 뒤 엣지를 세워 정지.",
    "A partir de uma travessia suave, pivote ambos os skis através da pendente e coloque cantos até parar.")
add("From a traverse, pressure the outside ski through a small C, then switch sides.",
    "Depuis une traversée, chargez le ski extérieur dans un petit C, puis changez de côté.",
    "Aus der Schrägfahrt den Außenski durch ein kleines C belasten, dann Seite wechseln.",
    "Desde una travesía, carga el esquí exterior en una C pequeña y cambia de lado.",
    "Da una diagonale, carica lo sci esterno in una piccola C, poi cambia lato.",
    "斜滑降から外側スキーに圧をかけて小さなCを描き、側を交代。",
    "트래버스에서 바깥쪽 스키에 프레셔를 주어 작은 C를 그린 뒤 방향을 바꿉니다.",
    "A partir de uma travessia, pressione o ski exterior num pequeno C e mude de lado.")
add("From the skid branch: absorb and stay on snow; do not jump.",
    "Depuis la branche dérapage : absorbez et restez sur la neige ; ne sautez pas.",
    "Vom Drift-Zweig: absorbieren und auf dem Schnee bleiben; nicht springen.",
    "Desde la rama de derrape: absorbe y quédate en la nieve; no saltes.",
    "Dal ramo derapata: assorbi e resta sulla neve; non saltare.",
    "スキッド枝から：吸収して雪面に残る。ジャンプしない。",
    "스키드 가지에서: 흡수하고 눈 위에 머무르세요. 점프하지 마세요.",
    "A partir do ramo de derrapagem: absorva e fique na neve; não salte.")
add("Front view", "Vue de face", "Frontalansicht", "Vista frontal", "Vista frontale", "正面ビュー", "정면 뷰", "Vista frontal")
add("Frontal", "Frontal", "Frontal", "Frontal", "Frontale", "正面", "정면", "Frontal")
add("Gate", "Critère clé", "Tor / Gate", "Criterio clave", "Gate", "ゲート（必須項）", "게이트（필수）", "Critério-chave")
add("Gate metrics decide advancement; the rest are diagnostic.",
    "Les métriques clés décident de la progression ; le reste est diagnostique.",
    "Gate-Metriken entscheiden über den Aufstieg; der Rest ist diagnostisch.",
    "Las métricas clave deciden el avance; el resto es diagnóstico.",
    "Le metriche gate decidono l’avanzamento; il resto è diagnostico.",
    "ゲート指標が進級を決め、残りは診断用です。",
    "게이트 지표가 진급을 결정하고, 나머지는 진단용입니다.",
    "As métricas-chave decidem o avanço; o resto é diagnóstico.")
add("Gates passed", "Critères réussis", "Tore bestanden", "Criterios superados", "Gate superati", "ゲート合格", "게이트 통과", "Critérios cumpridos")
add("Gender", "Genre", "Geschlecht", "Género", "Genere", "性別", "성별", "Género")
add("Gentle-slope wedge brake",
    "Freinage en chasse-neige sur pente douce",
    "Pflugbremsen auf leichter Piste",
    "Frenado en cuña en pendiente suave",
    "Frenata a spazzaneve su pendio dolce",
    "緩斜面プルークブレーキ",
    "완만 슬로프 플루크 제동",
    "Travagem em cunha em pendente suave")
add("Glide straight in a wedge and stop on purpose.",
    "Glissez droit en chasse-neige et arrêtez-vous volontairement.",
    "Im Pflug geradeaus gleiten und gezielt stoppen.",
    "Desliza en línea en cuña y párate a propósito.",
    "Scivola dritto a spazzaneve e fermati di proposito.",
    "プルークで直進し、意図して止まる。",
    "플루크로 직진한 뒤 의도적으로 멈추세요.",
    "Deslize em linha em cunha e pare de propósito.")
add("Goal", "Objectif", "Ziel", "Objetivo", "Obiettivo", "目標", "목표", "Objetivo")
add("Grant camera access to run pose tracking.",
    "Autorisez la caméra pour le suivi de pose.",
    "Kamerazugriff für Pose-Tracking erlauben.",
    "Concede acceso a la cámara para el seguimiento de pose.",
    "Consenti l’accesso alla fotocamera per il tracking della posa.",
    "姿勢トラッキングのためカメラへのアクセスを許可してください。",
    "자세 추적을 위해 카메라 접근을 허용하세요.",
    "Conceda acesso à câmara para o rastreio de postura.")
add("Green", "Verte", "Grün", "Verde", "Verde", "緑", "그린", "Verde")
add("Green run", "Piste verte", "Grüne Piste", "Pista verde", "Pista verde", "初級斜面（緑）", "초급 슬로프（그린）", "Pista verde")
add("Groomed-run recreational alpine",
    "Ski alpin loisir sur piste damée",
    "Freizeit-Alpinski auf präparierter Piste",
    "Esquí alpino recreativo en pista pisada",
    "Sci alpino amatoriale su pista battuta",
    "整備ゲレンデのレクリエーション・アルペン",
    "정비 슬로프 레크리에이션 알파인",
    "Ski alpino recreativo em pista preparada")
add("Hands in view", "Mains visibles devant", "Hände im Blickfeld", "Manos a la vista", "Mani in vista", "手が前方に見える", "손이 앞에 보이게", "Mãos à vista")
add("Hands low", "Mains basses", "Hände tief", "Manos bajas", "Mani basse", "手を低く", "손을 낮게", "Mãos baixas")
add("Hard rule", "Règle stricte", "Harte Regel", "Regla dura", "Regola rigida", "硬性ルール", "하드 룰", "Regra rígida")
add("Hardpack", "Neige dure", "Hartschnee", "Nieve dura", "Neve dura", "ハードパック", "하드팩", "Neve dura")
add("Height", "Taille", "Größe", "Altura", "Altezza", "身長", "키", "Altura")
add("Heuristic inclination and parallel stance, not FIS. Learn one-ski first.",
    "Inclinaison et parallélisme heuristiques, pas FIS. Maîtrisez d’abord le ski unique.",
    "Heuristische Neigung und Parallelstellung, nicht FIS. Zuerst Einbein beherrschen.",
    "Inclinación y paralelo heurísticos, no FIS. Domina primero el monoesquí.",
    "Inclinazione e parallelo euristici, non FIS. Prima impara lo sci singolo.",
    "経験則の内傾とパラレル、非FIS。まずワン<|reserved_token_163702|>スキーを。",
    "휴리스틱 인클라인·패러렐, 비 FIS. 먼저 원스키를 익히세요.",
    "Inclinação e paralelo heurísticos, não FIS. Domine primeiro o ski único.")

# Fix the accidental token in Japanese line above - rewrite that entry properly below in fixup
# Continue adding more entries...

def as_dict() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for en, fr, de, es, it, ja, ko, pt in ROWS:
        ja = ja.replace("<|reserved_token_163702|>", "")
        out[en] = {"fr": fr, "de": de, "es": es, "it": it, "ja": ja, "ko": ko, "pt": pt}
    return out
