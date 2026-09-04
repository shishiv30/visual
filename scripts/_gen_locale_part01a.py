# -*- coding: utf-8 -*-
"""Bulk-generate remaining ski locale fills (keys not in part00).

Professional register: ESF / DSV / RFEDI / SAJ / KSIA / PT alpine coaching.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = json.loads((ROOT / "tmp_i18n_keys.json").read_text(encoding="utf-8"))
DONE = json.loads((ROOT / "locales" / "_ski_locale_fills" / "part00.json").read_text(encoding="utf-8"))
OUT = ROOT / "locales" / "_ski_locale_fills"

# Compact rows: en, fr, de, es, it, ja, ko, pt
# Generated in chunks below and merged.


def row(en: str, fr: str, de: str, es: str, it: str, ja: str, ko: str, pt: str) -> dict:
    return {en: {"fr": fr, "de": de, "es": es, "it": it, "ja": ja, "ko": ko, "pt": pt}}


def merge(chunks: list[dict[str, dict[str, str]]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for c in chunks:
        out.update(c)
    return out


# --- chunk A: 100-199 ---
A: dict[str, dict[str, str]] = {}
A.update(row(
    "Display only: boxes, rails, and jumps with a coach; the app does not score them.",
    "Affichage seul : boxes, rails et sauts avec un coach ; l’app ne les note pas.",
    "Nur Anzeige: Boxes, Rails und Sprünge mit Coach; die App bewertet sie nicht.",
    "Solo visualización: cajas, rails y saltos con un coach; la app no los puntúa.",
    "Solo visualizzazione: box, rail e salti con un coach; l’app non li valuta.",
    "表示のみ：ボックス・レール・ジャンプはコーチと。本アプリは採点しません。",
    "표시 전용: 박스·레일·점프는 코치와. 앱은 채점하지 않습니다.",
    "Só visualização: boxes, rails e saltos com um coach; a app não os pontua.",
))
A.update(row(
    "Display only: this app does not time gates.",
    "Affichage seul : cette app ne chronomètre pas les portes.",
    "Nur Anzeige: diese App stoppt keine Tore.",
    "Solo visualización: esta app no cronometra puertas.",
    "Solo visualizzazione: questa app non cronometra i cancelli.",
    "表示のみ：本アプリは旗門のタイム計測をしません。",
    "표시 전용: 이 앱은 게이트 계시하지 않습니다.",
    "Só visualização: esta app não cronometra portões.",
))
A.update(row(
    "Display only: v2 video does not classify switch.",
    "Affichage seul : la vidéo v2 ne classe pas le switch.",
    "Nur Anzeige: v2-Video klassifiziert Switch nicht.",
    "Solo visualización: el vídeo v2 no clasifica el switch.",
    "Solo visualizzazione: il video v2 non classifica lo switch.",
    "表示のみ：v2動画はスイッチを自動判定しません。",
    "표시 전용: v2 동영상은 스위치를 분류하지 않습니다.",
    "Só visualização: o vídeo v2 não classifica switch.",
))
A.update(row(
    "Distances are normalized to this skier's leg length.",
    "Les distances sont normalisées à la longueur de jambe de ce skieur.",
    "Distanzen sind auf die Beinlänge dieses Skifahrers normalisiert.",
    "Las distancias se normalizan a la longitud de pierna de este esquiador.",
    "Le distanze sono normalizzate alla lunghezza di gamba di questo sciatore.",
    "距離はこの滑走者の脚長で正規化しています。",
    "거리는 이 스키어의 다리 길이로 정규화됩니다.",
    "As distâncias são normalizadas ao comprimento da perna deste esquiador.",
))
A.update(row(
    "Do not spin the shoulders with the skis.",
    "Ne faites pas tourner les épaules avec les skis.",
    "Schultern nicht mit den Skiern mitdrehen.",
    "No gires los hombros con los esquís.",
    "Non far girare le spalle con gli sci.",
    "肩をスキーと一緒に回し込まない。",
    "어깨를 스키와 함께 돌리지 마세요.",
    "Não rode os ombros com os skis.",
))
A.update(row(
    "Don't land or absorb with locked, straight legs.",
    "N’atterrissez pas ni n’absorbez jambes verrouillées et tendues.",
    "Nicht mit durchgedrückten, gestreckten Beinen landen oder federn.",
    "No aterrices ni absorbas con piernas bloqueadas y rectas.",
    "Non atterrare né assorbire a gambe bloccate e tese.",
    "ロックした直脚で着地・吸収しない。",
    "잠긴 직다리로 착지하거나 흡수하지 마세요.",
    "Não aterre nem absorva com pernas bloqueadas e esticadas.",
))
A.update(row("Done", "Terminé", "Fertig", "Listo", "Fatto", "完了", "완료", "Concluído"))
A.update(row("Dose", "Dose", "Dosis", "Dosis", "Dose", "用量", "운동량", "Dose"))
A.update(row("Double black", "Double noire", "Doppelt schwarz", "Doble negra", "Doppia nera", "ダブルブラック", "더블 블랙", "Dupla preta"))
A.update(row("Double black run", "Piste double noire", "Doppelt schwarze Piste", "Pista doble negra", "Pista doppia nera", "最上級斜面（ダブルブラック）", "최상급 슬로프（더블 블랙）", "Pista dupla preta"))
A.update(row("Download", "Télécharger", "Herunterladen", "Descargar", "Scarica", "ダウンロード", "다운로드", "Transferir"))
A.update(row(
    "Draw a person box before confirming.",
    "Dessinez un cadre autour de la personne avant de confirmer.",
    "Personenrahmen zeichnen, bevor du bestätigst.",
    "Dibuja una caja sobre la persona antes de confirmar.",
    "Disegna un box sulla persona prima di confermare.",
    "確定する前に人物枠を描いてください。",
    "확인 전에 인물 박스를 그리세요.",
    "Desenhe uma caixa na pessoa antes de confirmar.",
))
A.update(row("Drills", "Exercices", "Drills", "Ejercicios", "Esercizi", "ドリル", "드릴", "Exercícios"))
A.update(row(
    "Dryland / flat",
    "Sec / plat",
    "Trocken / flach",
    "Seco / llano",
    "Asciutto / piano",
    "陸トレ / 平坦",
    "지상 / 평지",
    "Seco / plano",
))
A.update(row(
    "Dynamic parallel: rhythm and poles",
    "Parallèle dynamique : rythme et bâtons",
    "Dynamischer Parallelschwung: Rhythmus und Stöcke",
    "Paralelo dinámico: ritmo y bastones",
    "Parallelo dinamico: ritmo e bastoncini",
    "ダイナミック・パラレル：リズムとポール",
    "다이내믹 패러렐: 리듬과 폴",
    "Paralelo dinâmico: ritmo e bastões",
))
A.update(row(
    "Early edge on firm snow",
    "Carre précoce sur neige dure",
    "Früher Kanteneinsatz auf hartem Schnee",
    "Canto temprano en nieve dura",
    "Lama precoce su neve dura",
    "硬雪での早めのエッジ",
    "하드팩에서 이른 엣지",
    "Canto precoce em neve dura",
))
A.update(row(
    "Easy slope, parallel or wedge: tap the downhill pole each turn.",
    "Pente douce, parallèle ou chasse-neige : tapotez le bâton aval à chaque virage.",
    "Leichte Piste, parallel oder Pflug: talwärtigen Stock bei jeder Kurve antippen.",
    "Pendiente suave, paralelo o cuña: toca el bastón de valle en cada curva.",
    "Pendio facile, parallelo o spazzaneve: tocca il bastoncino a valle a ogni curva.",
    "緩斜面のパラレルまたはプルーク：毎ターン山下ポールを軽くタップ。",
    "완만한 슬로프, 패러렐 또는 플루크: 매 턴 밸리 폴을 가볍게 탭.",
    "Pendente suave, paralelo ou cunha: toque o bastão de vale em cada curva.",
))
A.update(row("Edge angle (proxy)", "Angle de carre (proxy)", "Kantenwinkel (Proxy)", "Ángulo de canto (proxy)", "Angolo di lama (proxy)", "エッジ角（推定）", "엣지 각도（추정）", "Ângulo de canto (proxy)"))
A.update(row(
    "Edge changes faster than long-radius.",
    "Changements de carre plus rapides qu’en grand rayon.",
    "Kantenwechsel schneller als im langen Radius.",
    "Cambios de canto más rápidos que en radio largo.",
    "Cambi di lama più rapidi del raggio lungo.",
    "ロングターンより速いエッジチェンジ。",
    "롱턴보다 빠른 엣지 체인지.",
    "Mudanças de canto mais rápidas do que em raio longo.",
))
A.update(row(
    "Edge release and re-set",
    "Libération puis reprise de carre",
    "Kante lösen und neu setzen",
    "Liberar y volver a poner el canto",
    "Rilasciare e riprendere la lama",
    "エッジ解除と再セット",
    "엣지 해제와 재설정",
    "Libertar e voltar a colocar o canto",
))
A.update(row("Edge-change time", "Temps de changement de carre", "Kantenwechselzeit", "Tiempo de cambio de canto", "Tempo di cambio lama", "エッジチェンジ時間", "엣지 체인지 시간", "Tempo de mudança de canto"))
A.update(row("Edging and steering", "Prise de carre et direction", "Kanteneinsatz und Steuerung", "Canting y dirección", "Presa di lama e sterzo", "エッジングと操舵", "에징과 스티어링", "Canting e direção"))
A.update(row("Effective frame rate", "Cadence d’images effective", "Effektive Bildrate", "Frecuencia de fotogramas efectiva", "Frequenza fotogrammi effettiva", "有効フレームレート", "유효 프레임레이트", "Taxa de fotogramas efetiva"))
A.update(row("Effective {fps:.1f} fps", "{fps:.1f} fps effectifs", "Effektiv {fps:.1f} fps", "{fps:.1f} fps efectivos", "{fps:.1f} fps effettivi", "有効 {fps:.1f} fps", "유효 {fps:.1f} fps", "{fps:.1f} fps efetivos"))

# Write remaining rows for A (124-199) in a second data blob via exec of generated content
# Continue inline for critical ski coaching strings.

MORE_A = [
("Eight each side; if speed builds, reset to a traverse before stopping.",
 "Huit de chaque côté ; si la vitesse monte, repassez en traversée avant de vous arrêter.",
 "Acht je Seite; baut Tempo auf, erst wieder in die Schrägfahrt, dann stoppen.",
 "Ocho por lado; si sube la velocidad, vuelve a la travesía antes de parar.",
 "Otto per lato; se sale la velocità, torna in diagonale prima di fermarti.",
 "左右各8回。速度が上がったら斜滑降に戻してから止める。",
 "좌우 각 8회. 속도가 오르면 트래버스로 돌아온 뒤 멈추세요.",
 "Oito de cada lado; se a velocidade sobe, volte à travessia antes de parar."),
("Eight medium turns on the same pitch; cadence between long and short.",
 "Huit virages moyens sur la même pente ; cadence entre grand et petit rayon.",
 "Acht mittlere Schwünge auf derselben Neigung; Kadenz zwischen lang und kurz.",
 "Ocho curvas medias en la misma pendiente; cadencia entre radio largo y corto.",
 "Otto curve medie sullo stesso pendio; cadenza tra raggio lungo e corto.",
 "同一斜面で中ターン8本。ロングとショートの中間のリズム。",
 "같은 경사에서 미들 턴 8개. 롱과 숏 사이 리듬.",
 "Oito curvas médias na mesma pendente; cadência entre raio longo e curto."),
("Eight straight lines over round, shallow bumps.",
 "Huit lignes droites sur bosses rondes et peu marquées.",
 "Acht Geradeausfahrten über runde, flache Buckel.",
 "Ocho líneas rectas sobre baches redondos y bajos.",
 "Otto linee dritte su gobbe rotonde e basse.",
 "丸く浅いバンプ上を直滑降で8本。",
 "둥글고 얕은 범프 위 직활 8회.",
 "Oito linhas retas sobre bossas redondas e baixas."),
("Eight turns on green or blue; match the inside ski only in the last third of the turn.",
 "Huit virages sur verte ou bleue ; n’appariez le ski intérieur que dans le dernier tiers.",
 "Acht Schwünge auf grün oder blau; Innenski erst im letzten Drittel schließen.",
 "Ocho curvas en verde o azul; iguala el interior solo en el último tercio.",
 "Otto curve su verde o blu; affianca lo sci interno solo nell’ultimo terzo.",
 "緑または青で8ターン。内足はターン後半1/3でのみ寄せる。",
 "그린/블루에서 턴 8개. 안쪽 스키는 턴 후반 1/3에서만 맞추세요.",
 "Oito curvas em verde ou azul; iguale o ski interior só no último terço."),
("Elastic knees and ankles; not locked.",
 "Genoux et chevilles élastiques ; pas verrouillés.",
 "Elastische Knie und Knöchel; nicht durchgedrückt.",
 "Rodillas y tobillos elásticos; no bloqueados.",
 "Ginocchia e caviglie elastiche; non bloccate.",
 "膝と足首に弾性を。ロックしない。",
 "무릎·발목에 탄력을. 잠그지 마세요.",
 "Joelhos e tornozelos elásticos; não bloqueados."),
("Enter name, height, weight, and ski length, or pick a saved profile.",
 "Saisissez nom, taille, poids et longueur de ski, ou choisissez un profil enregistré.",
 "Name, Größe, Gewicht und Skilänge eingeben oder gespeichertes Profil wählen.",
 "Introduce nombre, altura, peso y longitud de esquí, o elige un perfil guardado.",
 "Inserisci nome, altezza, peso e lunghezza sci, oppure scegli un profilo salvato.",
 "氏名・身長・体重・スキー長を入力するか、保存済みプロフィールを選択。",
 "이름·키·체중·스키 길이를 입력하거나 저장된 프로필을 선택하세요.",
 "Introduza nome, altura, peso e comprimento do ski, ou escolha um perfil guardado."),
("Equipment", "Équipement", "Ausrüstung", "Equipamiento", "Attrezzatura", "装備", "장비", "Equipamento"),
("Equipment guidance is a starting range from height and weight, not a boot fitting.",
 "Les conseils d’équipement sont une plage de départ selon taille et poids, pas un fitting.",
 "Ausrüstungshinweise sind eine Startspanne aus Größe und Gewicht, kein Bootfitting.",
 "La guía de equipo es un rango inicial por altura y peso, no un fitting de bota.",
 "La guida attrezzatura è un intervallo iniziale da altezza e peso, non un fitting.",
 "装備ガイドは身長・体重からの目安範囲であり、ブーツフィッティングではありません。",
 "장비 안내는 키·체중 기준의 시작 범위이며 부츠 피팅이 아닙니다.",
 "A orientação de equipamento é um intervalo inicial por altura e peso, não um fitting."),
("Even turn rhythm", "Rythme de virage régulier", "Gleichmäßiger Schwungrhythmus", "Ritmo de curva uniforme", "Ritmo di curva uniforme", "均等なターンリズム", "고른 턴 리듬", "Ritmo de curva uniforme"),
("Export failed", "Échec de l’export", "Export fehlgeschlagen", "Error al exportar", "Esportazione non riuscita", "書き出し失敗", "내보내기 실패", "Falha na exportação"),
("Extend into the new turn and flex through the arc; count the rhythm out loud.",
 "Étendez-vous dans le nouveau virage et fléchissez dans l’arc ; comptez le rythme à voix haute.",
 "In den neuen Schwung strecken, durch den Bogen beugen; Rhythmus laut zählen.",
 "Extiéndete en la nueva curva y flexiona en el arco; cuenta el ritmo en voz alta.",
 "Estenditi nella nuova curva e fletti nell’arco; conta il ritmo ad alta voce.",
 "新ターンへ伸展し、弧の中で屈曲。リズムを声に出して数える。",
 "새 턴으로 펴고 아크 중 굴곡. 리듬을 소리 내어 세요.",
 "Estenda-se na nova curva e flexione no arco; conte o ritmo em voz alta."),
("Facebook", "Facebook", "Facebook", "Facebook", "Facebook", "Facebook", "Facebook", "Facebook"),
("Falling-leaf sideslip", "Feuille morte / dérapage latéral", "Falling Leaf / Seitwärtsrutschen", "Hoja caída / derrape lateral", "Falling leaf / derapata laterale", "フォーリングリーフ側滑", "폴링 리프 사이드슬립", "Falling leaf / derrapagem lateral"),
("Fast edge change, quieter shoulders. End of the groomed carve branch.",
 "Changement de carre rapide, épaules plus calmes. Fin de la branche carving piste.",
 "Schneller Kantenwechsel, ruhigere Schultern. Ende des Carving-Zweigs auf präparierter Piste.",
 "Cambio de canto rápido, hombros más quietos. Fin de la rama carving en pista.",
 "Cambio di lama rapido, spalle più quiete. Fine del ramo carving su pista battuta.",
 "速いエッジチェンジ、静かな肩。ゲレンデ・カービング枝の終点。",
 "빠른 엣지 체인지, 더 고요한 어깨. 정비 슬로프 카빙 가지의 끝.",
 "Mudança de canto rápida, ombros mais quietos. Fim do ramo carving em pista."),
("Faster edge changes without losing parallel inclination.",
 "Changements de carre plus rapides sans perdre l’inclinaison parallèle.",
 "Schnellere Kantenwechsel ohne parallele Neigung zu verlieren.",
 "Cambios de canto más rápidos sin perder la inclinación paralela.",
 "Cambi di lama più rapidi senza perdere l’inclinazione parallela.",
 "パラレル内傾を保ったままエッジチェンジを速く。",
 "패러렐 인클라인 유지한 채 더 빠른 엣지 체인지.",
 "Mudanças de canto mais rápidas sem perder a inclinação paralela."),
("Faults and fixes", "Erreurs et corrections", "Fehler und Korrekturen", "Errores y correcciones", "Errori e correzioni", "よくあるミスと修正", "실수와 교정", "Erros e correções"),
("Female", "Femme", "Weiblich", "Mujer", "Donna", "女性", "여성", "Feminino"),
("Few high-quality sets; do not train fatigue into poor form.",
 "Peu de séries, haute qualité ; ne laissez pas la fatigue dégrader la forme.",
 "Wenige, qualitativ hohe Sätze; Ermüdung nicht in schlechte Form trainieren.",
 "Pocas series de alta calidad; no entrenes la fatiga hasta deformar.",
 "Poche serie di alta qualità; non allenare la fatica fino a deformare.",
 "セットは少なく質を高く。疲労でフォームを崩さない。",
 "세트는 적고 질 높게. 피로로 폼이 무너지게 훈련하지 마세요.",
 "Poucas séries de alta qualidade; não treine a fadiga até degradar a forma."),
("Fewer traverses, linked absorption; still no air scoring.",
 "Moins de traversées, absorption enchaînée ; toujours pas de note d’air.",
 "Weniger Schrägfahrten, verkettete Absorption; weiterhin keine Air-Wertung.",
 "Menos travesías, absorción enlazada; sigue sin puntuación de air.",
 "Meno diagonali, assorbimento concatenato; ancora niente punteggio air.",
 "横切を減らし連続吸収。空中採点はなし。",
 "트래버스 줄이고 연결 흡수. 에어 채점은 없음.",
 "Menos travessias, absorção encadeada; ainda sem pontuação de air."),
("Filmed almost face-on: fore/aft balance cannot be measured. Film from a quarter angle, behind and to one side.",
 "Presque de face : l’équilibre avant/arrière ne peut pas être mesuré. Filmez en trois-quarts, derrière et de côté.",
 "Fast frontal: Vor-/Rücklage nicht messbar. Aus Viertelwinkel hinterlich seitlich filmen.",
 "Casi de frente: el equilibrio anteroposterior no se puede medir. Filma en tres cuartos, detrás y a un lado.",
 "Quasi frontale: l’equilibrio antero-posteriore non è misurabile. Riprendi a tre quarti, da dietro e di lato.",
 "ほぼ正面：前後バランスは測定不可。斜め後方（クォーター）から撮影を。",
 "거의 정면: 전후 밸런스 측정 불가. 사선 후방(쿼터)에서 촬영하세요.",
 "Quase de frente: o equilíbrio anteroposterior não pode ser medido. Filme a três quartos, atrás e de lado."),
("Filmed almost side-on: stance, edging and lean cannot be measured. Film from a quarter angle, behind and to one side.",
 "Presque de profil : écartement, carres et inclinaison ne peuvent pas être mesurés. Filmez en trois-quarts.",
 "Fast seitlich: Standbreite, Kanten und Neigung nicht messbar. Aus Viertelwinkel filmen.",
 "Casi de perfil: base, cantos e inclinación no se pueden medir. Filma en tres cuartos.",
 "Quasi di profilo: base, lame e inclinazione non misurabili. Riprendi a tre quarti.",
 "ほぼ真横：スタンス・エッジ・内傾は測定不可。斜め後方から撮影を。",
 "거의 측면: 스탠스·엣지·인클라인 측정 불가. 사선 후방에서 촬영하세요.",
 "Quase de perfil: base, cantos e inclinação não podem ser medidos. Filme a três quartos."),
("Filmed too face-on to measure this.",
 "Trop de face pour mesurer ceci.",
 "Zu frontal, um dies zu messen.",
 "Demasiado de frente para medir esto.",
 "Troppo frontale per misurare questo.",
 "正面すぎてこの項目は測定できません。",
 "너무 정면이라 이 항목을 측정할 수 없습니다.",
 "Demasiado de frente para medir isto."),
("Filmed too side-on to measure this.",
 "Trop de profil pour mesurer ceci.",
 "Zu seitlich, um dies zu messen.",
 "Demasiado de perfil para medir esto.",
 "Troppo di profilo per misurare questo.",
 "真横すぎてこの項目は測定できません。",
 "너무 측면이라 이 항목을 측정할 수 없습니다.",
 "Demasiado de perfil para medir isto."),
("Filming and disclaimer", "Tournage et avertissement", "Filmen und Hinweis", "Filmación y aviso", "Ripresa e avvertenza", "撮影と免責", "촬영과 면책", "Filmagem e aviso"),
("Filming and scoring", "Tournage et notation", "Filmen und Bewertung", "Filmación y puntuación", "Ripresa e valutazione", "撮影と採点", "촬영과 채점", "Filmagem e pontuação"),
("Filming checklist for the next clip", "Checklist tournage pour le prochain clip", "Filmliste für den nächsten Clip", "Lista de filmación para el próximo clip", "Checklist ripresa per la prossima clip", "次クリップの撮影チェックリスト", "다음 클립 촬영 체크리스트", "Lista de filmagem para o próximo clipe"),
("Filming quality", "Qualité de prise de vue", "Aufnahmequalität", "Calidad de filmación", "Qualità di ripresa", "撮影品質", "촬영 품질", "Qualidade de filmagem"),
("Firm snow and ice", "Neige dure et glace", "Harter Schnee und Eis", "Nieve dura y hielo", "Neve dura e ghiaccio", "硬雪とアイス", "하드팩과 아이스", "Neve dura e gelo"),
("First slide and equipment", "Premiers glissés et équipement", "Erste Gleitung und Ausrüstung", "Primer deslizamiento y equipo", "Prima scivolata e attrezzatura", "初めての滑走と装備", "첫 활강과 장비", "Primeiro deslize e equipamento"),
("Fix cue", "Consigne de correction", "Korrektur-Cue", "Consigna de corrección", "Cue di correzione", "修正キュー", "교정 큐", "Indicação de correção"),
]

for en, fr, de, es, it, ja, ko, pt in MORE_A:
    A.update(row(en, fr, de, es, it, ja, ko, pt))

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "part01a.json").write_text(json.dumps(A, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("part01a", len(A))
