# -*- coding: utf-8 -*-
import json
from pathlib import Path

def L(fr, de, es, it, ja, ko, pt):
    return {"fr": fr, "de": de, "es": es, "it": it, "ja": ja, "ko": ko, "pt": pt}

T = {}

def p(en, fr, de, es, it, ja, ko, pt):
    T[en] = L(fr, de, es, it, ja, ko, pt)

# --- coaching + UI batch (professional ski register) ---
p("Flatten both skis to slip sideways, then edge again to stop — neither a locked edge nor a free slide.",
  "Mettez les deux skis à plat pour glisser de côté, puis remettez les carres pour vous arrêter — ni carre bloquée ni glissade libre.",
  "Beide Ski flach stellen und seitlich gleiten, dann wieder kanten und stoppen — weder blockierte Kante noch freies Rutschen.",
  "Pon ambos esquís planos para deslizar de lado y vuelve a cantar para parar: ni canto bloqueado ni desliz libre.",
  "Metti entrambi gli sci piatti per scivolare di lato, poi riprendi le lame e fermati — né lama bloccata né scivolata libera.",
  "両スキーをフラットにして横へ滑らせ、再エッジで止める——ロックしたエッジでも暴走スライドでもない。",
  "양 스키를 평평히 해 옆으로 미끄러진 뒤 다시 엣지를 세워 멈추세요 — 잠긴 엣지도, 통제 없는 슬라이드도 아님.",
  "Ponha ambos os skis planos para escorregar de lado e volte a cantar para parar — nem canto bloqueado nem deslize livre.")
p("Flex and extend to surface the skis","Fléchissez et étendez pour faire remonter les skis","Beugen und strecken, damit die Ski aufschwimmen","Flexiona y extiende para hacer flotar los esquís","Fletti ed estendi per far affiorare gli sci","蹲伸でスキーを浮かせる","굴신으로 스키를 띄우기","Flexione e estenda para fazer os skis emergir")
p("Flex for rhythm","Fléchir pour le rythme","Beugen für den Rhythmus","Flexión para el ritmo","Flessione per il ritmo","リズムのための屈曲","리듬을 위한 굴곡","Flexão para o ritmo")
p("Flex into the turn","Fléchir dans le virage","In den Schwung beugen","Flexionar hacia la curva","Flettere nella curva","ターンへ入りながら屈曲","턴 진입 굴곡","Flexionar na curva")
p("Flex-and-extend rhythm","Rythme flexion–extension","Beuge-Streck-Rhythmus","Ritmo flexión–extensión","Ritmo flessione–estensione","蹲伸リズム","굴신 리듬","Ritmo flexão–extensão")
p("Follow","Suivi","Follow","Seguimiento","Follow","フォロー","팔로우","Seguir")
p("Follow camera","Caméra en suivi","Follow-Kamera","Cámara en seguimiento","Camera a seguire","フォローカメラ","팔로우 카메라","Câmara a seguir")
p("Follow-cam; one alpine skier in frame.","Caméra en suivi ; un seul skieur alpin dans le cadre.","Follow-Cam; ein alpiner Skifahrer im Bild.","Cámara en seguimiento; un solo esquiador alpino en cuadro.","Camera a seguire; un solo sciatore alpino in campo.","フォロー撮影。画面にはアルペンスキーヤー1人。","팔로우 촬영. 화면에 알파인 스키어 한 명.","Câmara a seguir; um único esquiador alpino no enquadramento.")
p("For your profile","Pour votre profil","Für Ihr Profil","Para tu perfil","Per il tuo profilo","あなたのプロフィール向け","내 프로필 기준","Para o seu perfil")
p("Format","Format","Format","Formato","Formato","形式","형식","Formato")
p("Four posture scores are coach heuristics (0–100), not lab biomechanics; they are not true speed, meter turn radius, or peak ski pressure.",
  "Les quatre scores de posture sont des heuristiques de coach (0–100), pas de la biomécanique de labo ; ce ne sont ni une vraie vitesse, ni un rayon en mètres, ni une pression de ski de pointe.",
  "Vier Haltungswerte sind Coach-Heuristiken (0–100), keine Labor-Biomechanik; keine echte Geschwindigkeit, kein Meter-Radius, kein Peak-Skidruck.",
  "Las cuatro puntuaciones de postura son heurísticas de coach (0–100), no biomecánica de laboratorio; no son velocidad real, radio en metros ni presión máxima.",
  "I quattro punteggi di postura sono euristiche da coach (0–100), non biomeccanica da laboratorio; non sono velocità vera, raggio in metri né pressione di picco.",
  "姿勢の4得点はコーチ経験則（0–100）であり実験室の生体力学ではありません。実速度・メートル半径・板底ピーク圧ではありません。",
  "자세 4점수는 코치 휴리스틱(0–100)이며 실험실 생체역학이 아닙니다. 실제 속도·미터 반경·스키 피크 압력이 아닙니다.",
  "As quatro pontuações de postura são heurísticas de coach (0–100), não biomecânica de laboratório; não são velocidade real, raio em metros nem pressão de pico.")
p("Frame locator JSON copied","JSON du localisateur d’image copié","Frame-Locator-JSON kopiert","JSON del localizador de fotograma copiado","JSON localizzatore frame copiato","フレーム位置JSONをコピーしました","프레임 위치 JSON 복사됨","JSON do localizador de fotograma copiado")
p("From a gentle traverse, pivot both skis across the hill and set the edges to a stop.",
  "Depuis une traversée douce, pivotez les deux skis à travers la pente et posez les carres jusqu’à l’arrêt.",
  "Aus einer leichten Schrägfahrt beide Ski quer zum Hang drehen und kanten bis zum Stopp.",
  "Desde una travesía suave, pivota ambos esquís a través de la pendiente y planta cantos hasta parar.",
  "Da una diagonale dolce, pivota entrambi gli sci attraverso il pendio e metti le lame fino all’arresto.",
  "緩い斜滑降から両スキーを斜面横断にピボットし、エッジを立てて停止。",
  "완만한 트래버스에서 양 스키를 사면 가로로 피벗한 뒤 엣지를 세워 정지.",
  "A partir de uma travessia suave, pivote ambos os skis através da pendente e coloque cantos até parar.")
p("From a traverse, pressure the outside ski through a small C, then switch sides.",
  "Depuis une traversée, chargez le ski extérieur dans un petit C, puis changez de côté.",
  "Aus der Schrägfahrt den Außenski durch ein kleines C belasten, dann Seite wechseln.",
  "Desde una travesía, carga el esquí exterior en una C pequeña y cambia de lado.",
  "Da una diagonale, carica lo sci esterno in una piccola C, poi cambia lato.",
  "斜滑降から外側スキーに圧をかけて小さなCを描き、側を交代。",
  "트래버스에서 바깥쪽 스키에 프레셔를 주어 작은 C를 그린 뒤 방향을 바꿉니다.",
  "A partir de uma travessia, pressione o ski exterior num pequeno C e mude de lado.")
p("From the skid branch: absorb and stay on snow; do not jump.",
  "Depuis la branche dérapage : absorbez et restez sur la neige ; ne sautez pas.",
  "Vom Drift-Zweig: absorbieren und auf dem Schnee bleiben; nicht springen.",
  "Desde la rama de derrape: absorbe y quédate en la nieve; no saltes.",
  "Dal ramo derapata: assorbi e resta sulla neve; non saltare.",
  "スキッド枝から：吸収して雪面に残る。ジャンプしない。",
  "스키드 가지에서: 흡수하고 눈 위에 머무르세요. 점프하지 마세요.",
  "A partir do ramo de derrapagem: absorva e fique na neve; não salte.")
p("Front view","Vue de face","Frontalansicht","Vista frontal","Vista frontale","正面ビュー","정면 뷰","Vista frontal")
p("Frontal","Frontal","Frontal","Frontal","Frontale","正面","정면","Frontal")
p("Gate","Critère clé","Gate","Criterio clave","Gate","ゲート（必須）","게이트（필수）","Critério-chave")
p("Gate metrics decide advancement; the rest are diagnostic.",
  "Les métriques clés décident de la progression ; le reste est diagnostique.",
  "Gate-Metriken entscheiden über den Aufstieg; der Rest ist diagnostisch.",
  "Las métricas clave deciden el avance; el resto es diagnóstico.",
  "Le metriche gate decidono l’avanzamento; il resto è diagnostico.",
  "ゲート指標が進級を決め、残りは診断用です。",
  "게이트 지표가 진급을 결정하고, 나머지는 진단용입니다.",
  "As métricas-chave decidem o avanço; o resto é diagnóstico.")
p("Gates passed","Critères réussis","Tore bestanden","Criterios superados","Gate superati","ゲート合格","게이트 통과","Critérios cumpridos")
p("Gender","Genre","Geschlecht","Género","Genere","性別","성별","Género")
p("Gentle-slope wedge brake","Freinage en chasse-neige sur pente douce","Pflugbremsen auf leichter Piste","Frenado en cuña en pendiente suave","Frenata a spazzaneve su pendio dolce","緩斜面プルークブレーキ","완만 슬로프 플루크 제동","Travagem em cunha em pendente suave")
p("Glide straight in a wedge and stop on purpose.","Glissez droit en chasse-neige et arrêtez-vous volontairement.","Im Pflug geradeaus gleiten und gezielt stoppen.","Desliza en línea en cuña y párate a propósito.","Scivola dritto a spazzaneve e fermati di proposito.","プルークで直進し、意図して止まる。","플루크로 직진한 뒤 의도적으로 멈추세요.","Deslize em linha em cunha e pare de propósito.")
p("Goal","Objectif","Ziel","Objetivo","Obiettivo","目標","목표","Objetivo")
p("Grant camera access to run pose tracking.","Autorisez la caméra pour le suivi de pose.","Kamerazugriff für Pose-Tracking erlauben.","Concede acceso a la cámara para el seguimiento de pose.","Consenti l’accesso alla fotocamera per il tracking della posa.","姿勢トラッキングのためカメラへのアクセスを許可してください。","자세 추적을 위해 카메라 접근을 허용하세요.","Conceda acesso à câmara para o rastreio de postura.")
p("Green","Verte","Grün","Verde","Verde","緑","그린","Verde")
p("Green run","Piste verte","Grüne Piste","Pista verde","Pista verde","初級斜面（緑）","초급 슬로프（그린）","Pista verde")
p("Groomed-run recreational alpine","Ski alpin loisir sur piste damée","Freizeit-Alpinski auf präparierter Piste","Esquí alpino recreativo en pista pisada","Sci alpino amatoriale su pista battuta","整備ゲレンデのレクリエーション・アルペン","정비 슬로프 레크리에이션 알파인","Ski alpino recreativo em pista preparada")
p("Hands in view","Mains visibles devant","Hände im Blickfeld","Manos a la vista","Mani in vista","手が前方に見える","손이 앞에 보이게","Mãos à vista")
p("Hands low","Mains basses","Hände tief","Manos bajas","Mani basse","手を低く","손을 낮게","Mãos baixas")
p("Hard rule","Règle stricte","Harte Regel","Regla dura","Regola rigida","硬性ルール","하드 룰","Regra rígida")
p("Hardpack","Neige dure","Hartschnee","Nieve dura","Neve dura","ハードパック","하드팩","Neve dura")
p("Height","Taille","Größe","Altura","Altezza","身長","키","Altura")
p("Heuristic inclination and parallel stance, not FIS. Learn one-ski first.",
  "Inclinaison et parallélisme heuristiques, pas FIS. Maîtrisez d’abord le ski unique.",
  "Heuristische Neigung und Parallelstellung, nicht FIS. Zuerst Einbein beherrschen.",
  "Inclinación y paralelo heurísticos, no FIS. Domina primero el monoesquí.",
  "Inclinazione e parallelo euristici, non FIS. Prima impara lo sci singolo.",
  "経験則の内傾とパラレル、非FIS。まずワン・スキーを。",
  "휴리스틱 인클라인·패러렐, 비 FIS. 먼저 원스키를 익히세요.",
  "Inclinação e paralelo heurísticos, não FIS. Domine primeiro o ski único.")
p("Heuristic score (0-100, not FIS)","Score heuristique (0-100, pas FIS)","Heuristische Punktzahl (0-100, nicht FIS)","Puntuación heurística (0-100, no FIS)","Punteggio euristico (0-100, non FIS)","経験則スコア（0-100、非FIS）","휴리스틱 점수 (0-100, 비 FIS)","Pontuação heurística (0-100, não FIS)")
p("Heuristic: steer with the legs — rotate the femurs so the ski tips turn while the torso stays quiet.",
  "Heuristique : dirigez avec les jambes — tournez les fémurs pour que les spatules pivotent, le buste reste calme.",
  "Heuristik: mit den Beinen steuern — Femurs drehen, damit die Schaufeln drehen, Oberkörper ruhig.",
  "Heurística: dirige con las piernas — rota los fémures para que giren las espátulas, el torso quieto.",
  "Euristica: sterza con le gambe — ruota i femori perché le punte girino, il busto resta quieto.",
  "経験則：脚で操舵——大腿を回してチップを向け、上体は静かに。",
  "휴리스틱: 다리로 스티어 — 대퇴를 돌려 팁이 돌게 하고, 상체는 고요히.",
  "Heurística: direcione com as pernas — rode os fémures para as pontas virarem, tronco quieto.")
p("Higher cadence without losing inclination.","Cadence plus élevée sans perdre l’inclinaison.","Höhere Kadenz ohne Neigung zu verlieren.","Mayor cadencia sin perder inclinación.","Cadenza più alta senza perdere inclinazione.","内傾を失わずにリズムを上げる。","인클라인 유지한 채 케이던스 올리기.","Cadência mais alta sem perder inclinação.")
p("Hip internal-rotation steering","Direction par rotation interne de hanche","Steuerung über Innenrotation der Hüfte","Dirección por rotación interna de cadera","Sterzo per rotazione interna dell’anca","股関節内旋による操舵","고관절 내회전 스티어링","Direção por rotação interna da anca")
p("Hips or ankles are missing in much of the clip.","Hanches ou chevilles manquent sur une grande partie du clip.","Hüften oder Knöchel fehlen in großen Teilen des Clips.","Faltan caderas o tobillos en gran parte del clip.","Mancano anche o caviglie in gran parte della clip.","クリップの多くで股関節または足首が欠落。","클립 상당 구간에서 엉덩이 또는 발목이 누락됨.","Ancas ou tornozelos em falta em grande parte do clipe.")
p("Hips over the feet","Hanches au-dessus des pieds","Hüften über den Füßen","Caderas sobre los pies","Anche sopra i piedi","股関節が足の上","엉덩이가 발 위","Ancas sobre os pés")
p("Hips over the feet; pressure into the ski.","Hanches au-dessus des pieds ; pression dans le ski.","Hüften über den Füßen; Druck in den Ski.","Caderas sobre los pies; presión en el esquí.","Anche sopra i piedi; pressione nello sci.","股関節が足の上、圧力をスキーへ。","엉덩이가 발 위, 프레셔를 스키로.","Ancas sobre os pés; pressão no ski.")
p("Hockey stop","Arrêt hockey","Hockey-Stopp","Parada hockey","Arresto hockey","ホッケーストップ","하키 스톱","Paragem hockey")
p("Hockey-stop capacity","Capacité d’arrêt hockey","Hockey-Stopp-Fähigkeit","Capacidad de parada hockey","Capacità di arresto hockey","ホッケーストップ能力","하키 스톱 능력","Capacidade de paragem hockey")
p("Hold a clean edge on hardpack: edge early, change edges quickly, no braking scrape.",
  "Tenez une carre propre sur neige dure : carre tôt, changez vite, sans freinage en dérapage.",
  "Saubere Kante auf Hartschnee: früh kanten, schnell wechseln, kein Brems-Schaben.",
  "Mantén un canto limpio en dura: canta pronto, cambia rápido, sin raspado de frenado.",
  "Tieni una lama pulita su neve dura: lama presto, cambia in fretta, senza raschiata frenante.",
  "ハードパックでクリーンなエッジ：早めに立て、素早く入れ替え、搓雪ブレーキなし。",
  "하드팩에서 클린 엣지: 일찍 세우고 빠르게 바꾸며 제동 스키드 없이.",
  "Mantenha um canto limpo em neve dura: cante cedo, mude rápido, sem raspagem de travagem.")
p("How to advance","Comment progresser","So steigst du auf","Cómo avanzar","Come avanzare","次の段階へ","다음 단계로","Como avançar")
p("How to film","Comment filmer","So filmen","Cómo filmar","Come riprendere","撮影のしかた","촬영 방법","Como filmar")
p("Ice","Glace","Eis","Hielo","Ghiaccio","アイス","아이스","Gelo")
p("Ideal terrain","Terrain idéal","Ideales Gelände","Terreno ideal","Terreno ideale","理想の地形","이상적 지형","Terreno ideal")
p("If not advancing, train toward","Si vous ne progressez pas, entraînez-vous vers","Wenn kein Aufstieg, trainiere Richtung","Si no avanzas, entrena hacia","Se non avanzi, allenati verso","進級しない場合の訓練目標","진급하지 못하면 다음을 향해 훈련","Se não avançar, treine para")
p("Import","Importer","Importieren","Importar","Importa","読み込み","가져오기","Importar")
p("Import failed","Échec de l’import","Import fehlgeschlagen","Error al importar","Importazione non riuscita","読み込み失敗","가져오기 실패","Falha na importação")
p("Import…","Importer…","Importieren…","Importar…","Importa…","読み込み…","가져오기…","Importar…")
p("In","Entrée","In","Entrada","In","イン","인","Entrada")
p("In {lo:.1f}s → out {hi:.1f}s (logical, original file unchanged)","Entrée {lo:.1f}s → sortie {hi:.1f}s (logique, fichier d’origine inchangé)","In {lo:.1f}s → Out {hi:.1f}s (logisch, Originaldatei unverändert)","Entrada {lo:.1f}s → salida {hi:.1f}s (lógico, archivo original intacto)","In {lo:.1f}s → out {hi:.1f}s (logico, file originale invariato)","イン {lo:.1f}s → アウト {hi:.1f}s（論理カット、原ファイルはそのまま）","인 {lo:.1f}s → 아웃 {hi:.1f}s (논리 컷, 원본 파일 유지)","Entrada {lo:.1f}s → saída {hi:.1f}s (lógico, ficheiro original intacto)")
p("Inclination","Inclinaison","Neigung","Inclinación","Inclinazione","インクライン","인클라인","Inclinação")
p("Inclination into the turn","Inclinaison vers l’intérieur du virage","Neigung in den Schwung","Inclinación hacia la curva","Inclinazione verso la curva","ターン内側へのインクライン","턴 안쪽으로의 인클라인","Inclinação para dentro da curva")
p("Indoors or flat ground for stance and single-leg strength.","En intérieur ou sur sol plat pour la posture et la force unilatérale.","Drinnen oder flach für Stellung und Einbein-Kraft.","Interior o suelo plano para postura y fuerza a una pierna.","Al chiuso o su piano per postura e forza monopodalica.","室内または平地でスタンスと片脚筋力。","실내 또는 평지에서 스탠스·편다리 근력.","Interior ou solo plano para postura e força unilátera.")
p("Injury risk","Risque de blessure","Verletzungsrisiko","Riesgo de lesión","Rischio di infortunio","怪我のリスク","부상 위험","Risco de lesão")
p("JPEG (*.jpg)","JPEG (*.jpg)","JPEG (*.jpg)","JPEG (*.jpg)","JPEG (*.jpg)","JPEG (*.jpg)","JPEG (*.jpg)","JPEG (*.jpg)")
p("Keep pole tips low and hands in front of the body, about waist to mid-torso, to time left–right turns.",
  "Gardez les pointes de bâton basses et les mains devant le corps, de la taille au milieu du torse, pour rythmer gauche–droite.",
  "Stockspitzen tief, Hände vor dem Körper etwa hüft- bis brusthoch, um Links–Rechts zu takten.",
  "Mantén las puntas de bastón bajas y las manos delante, de cintura a medio torso, para marcar izquierda–derecha.",
  "Tieni le punte dei bastoncini basse e le mani davanti, da vita a mezzo busto, per scandire sinistra–destra.",
  "ポール先端を低く、手は体の前・腰〜胸中ほど。左右ターンのタイミングに。",
  "폴 팁은 낮게, 손은 몸 앞·허리~가슴 중간. 좌우 턴 타이밍용.",
  "Mantenha as pontas dos bastões baixas e as mãos à frente, da cintura ao meio do tronco, para marcar esquerda–direita.")
p("Keep the arc round with both skis working; do not throw the skis sideways.",
  "Gardez l’arc rond avec les deux skis au travail ; ne jetez pas les skis de côté.",
  "Bogen rund halten, beide Ski arbeiten; Ski nicht seitlich werfen.",
  "Mantén el arco redondo con ambos esquís trabajando; no lances los esquís de lado.",
  "Tieni l’arco rotondo con entrambi gli sci al lavoro; non buttare gli sci di lato.",
  "両スキーが働き弧を丸く。横に投げない。",
  "양 스키가 일하며 아크를 둥글게. 옆으로 던지지 마세요.",
  "Mantenha o arco redondo com ambos os skis a trabalhar; não atire os skis de lado.")
p("Keep the camera steady — shaky or wild motion prevents a reliable stage assessment.",
  "Tenez la caméra stable — un mouvement secoué empêche une évaluation fiable du niveau.",
  "Kamera ruhig halten — Wackeln verhindert eine zuverlässige Stufenbewertung.",
  "Mantén la cámara estable — el movimiento brusco impide una evaluación fiable del nivel.",
  "Tieni la camera stabile — il movimento tremante impedisce una valutazione affidabile del livello.",
  "カメラを安定に——激しい揺れでは段階判定が信頼できません。",
  "카메라를 안정적으로 — 심한 흔들림은 단계 판정을 어렵게 합니다.",
  "Mantenha a câmara estável — movimento brusco impede uma avaliação fiável do nível.")
p("Key points","Points clés","Schlüsselpunkte","Puntos clave","Punti chiave","要点","핵심 포인트","Pontos-chave")
p("Knee absorption travel","Amplitude d’absorption des genoux","Knie-Absorptionsamplitude","Recorrido de absorción de rodilla","Corsa di assorbimento del ginocchio","膝の吸収ストローク","무릎 흡수 진폭","Amplitude de absorção do joelho")
p("Knee flex cadence matches the bumps.","La cadence de flexion du genou suit les bosses.","Kniebeuge-Kadenz folgt den Buckeln.","La cadencia de flexión de rodilla sigue los baches.","La cadenza di flessione del ginocchio segue le gobbe.","膝の屈伸リズムがバンプに合う。","무릎 굴신 리듬이 범프와 맞음.","A cadência de flexão do joelho acompanha as bossas.")
p("Knee flex range","Amplitude de flexion du genou","Kniebeugebereich","Rango de flexión de rodilla","Range di flessione del ginocchio","膝屈伸レンジ","무릎 굴신 범위","Amplitude de flexão do joelho")
p("Knee flex rate","Fréquence de flexion du genou","Kniebeugefrequenz","Frecuencia de flexión de rodilla","Frequenza di flessione del ginocchio","膝屈伸頻度","무릎 굴신 빈도","Frequência de flexão do joelho")
p("Knee tracking","Trajectoire du genou","Knieverlauf","Trayectoria de rodilla","Traiettoria del ginocchio","ニー・トラッキング","니 트래킹","Trajetória do joelho")
p("Knees track","Genoux alignés","Knie führen","Rodillas alineadas","Ginocchia allineate","膝が軌道を保つ","무릎이 궤도를 유지","Joelhos alinhados")
p("Knees track over the toes; don't let the knees collapse inward.",
  "Les genoux suivent les orteils ; ne laissez pas les genoux s’effondrer vers l’intérieur.",
  "Knie über den Zehen führen; nicht nach innen einknicken.",
  "Las rodillas siguen los dedos; no dejes que colapsen hacia dentro.",
  "I ginocchi seguono le punte dei piedi; non farli collassare verso dentro.",
  "膝はつま先の上。内へ崩れない。",
  "무릎은 발끝 위. 안쪽으로 무너지지 않게.",
  "Os joelhos seguem os dedos dos pés; não os deixe colapsar para dentro.")
p("Landmark quality","Qualité des repères","Landmark-Qualität","Calidad de landmarks","Qualità dei landmark","ランドマーク品質","랜드마크 품질","Qualidade dos landmarks")
p("Landmark quality {pct:.0f}%","Qualité des repères {pct:.0f}%","Landmark-Qualität {pct:.0f}%","Calidad de landmarks {pct:.0f}%","Qualità dei landmark {pct:.0f}%","ランドマーク品質 {pct:.0f}%","랜드마크 품질 {pct:.0f}%","Qualidade dos landmarks {pct:.0f}%")
p("Language","Langue","Sprache","Idioma","Lingua","言語","언어","Idioma")
p("Large knee travel; stay on snow rather than jumping.","Grande amplitude du genou ; restez sur la neige plutôt que de sauter.","Großer Kniehub; auf dem Schnee bleiben statt springen.","Gran recorrido de rodilla; quédate en la nieve en vez de saltar.","Ampia corsa del ginocchio; resta sulla neve invece di saltare.","膝の振幅を大きく。ジャンプより雪面に残る。","무릎 진폭을 크게. 점프보다 눈 위에.","Grande amplitude do joelho; fique na neve em vez de saltar.")
p("Left","Gauche","Links","Izquierda","Sinistra","左","왼쪽","Esquerda")
p("Left {left} · right {right}","Gauche {left} · droite {right}","Links {left} · rechts {right}","Izquierda {left} · derecha {right}","Sinistra {left} · destra {right}","左 {left} · 右 {right}","왼쪽 {left} · 오른쪽 {right}","Esquerda {left} · direita {right}")
p("Leading candidate","Candidat principal","Führender Kandidat","Candidato principal","Candidato principale","最有力候補","유력 후보","Candidato principal")
p("Left-right asymmetry","Asymétrie gauche–droite","Links-rechts-Asymmetrie","Asimetría izquierda–derecha","Asimmetria sinistra–destra","左右非対称","좌우 비대칭","Assimetria esquerda–direita")
p("Left-right turns, not a straight schuss.","Virages gauche–droite, pas un schuss droit.","Links-rechts-Schwünge, kein gerader Schuss.","Curvas izquierda–derecha, no un schuss recto.","Curve sinistra–destra, non uno schuss dritto.","左右ターン。直滑降一本ではない。","좌우 턴. 직선 슈스가 아님.","Curvas esquerda–direita, não um schuss reto.")
p("Legs and hips steer; do not use the shoulders as a steering wheel.",
  "Les jambes et les hanches dirigent ; n’utilisez pas les épaules comme un volant.",
  "Beine und Hüften steuern; Schultern nicht als Lenkrad nutzen.",
  "Piernas y caderas dirigen; no uses los hombros como volante.",
  "Gambe e anche sterzano; non usare le spalle come volante.",
  "脚と股関節で操舵。肩をハンドルにしない。",
  "다리와 엉덩이로 스티어. 어깨를 핸들로 쓰지 마세요.",
  "Pernas e ancas dirigem; não use os ombros como volante.")
p("Legs move; the torso stays quieter.","Les jambes bougent ; le buste reste plus calme.","Beine bewegen sich; der Oberkörper bleibt ruhiger.","Las piernas se mueven; el torso queda más quieto.","Le gambe si muovono; il busto resta più quieto.","脚は動き、上体は相対的に静か。","다리는 움직이고 상체는 더 고요히.","As pernas movem-se; o tronco fica mais quieto.")
p("Let the legs do the work.","Laissez les jambes faire le travail.","Die Beine arbeiten lassen.","Deja que las piernas hagan el trabajo.","Lascia lavorare le gambe.","脚に仕事をさせる。","다리가 일하게 하세요.","Deixe as pernas fazer o trabalho.")
p("Label skis","Annoter les skis","Ski markieren","Etiquetar esquís","Etichetta sci","スキーを注釈","스키 라벨","Etiquetar skis")
p("Optional: use Label skis on key frames before Start analysis.","Optionnel : utilisez Annoter les skis sur des images clés avant Lancer l’analyse.","Optional: vor Analyse starten Ski markieren auf Schlüsselbildern.","Opcional: usa Etiquetar esquís en fotogramas clave antes de Iniciar análisis.","Opzionale: usa Etichetta sci su fotogrammi chiave prima di Avvia analisi.","任意：分析開始前にキーフレームでスキーを注釈。","선택: 분석 시작 전 키 프레임에서 스키 라벨.","Opcional: use Etiquetar skis em fotogramas-chave antes de Iniciar análise.")
p("Like","J’aime","Gefällt mir","Me gusta","Mi piace","いいね","좋아요","Gosto")
p("Likely cause","Cause probable","Wahrscheinliche Ursache","Causa probable","Causa probabile","想定原因","추정 원인","Causa provável")
p("Link bumps near the fall line with less traversing.","Enchaînez les bosses près de la ligne de pente avec moins de traversées.","Buckel nahe der Falllinie verbinden, weniger Schrägfahrt.","Enlaza baches cerca de la línea de máxima pendiente con menos travesías.","Collega le gobbe vicino alla linea di massima pendenza con meno diagonali.","フォールライン近くでバンプを繋ぎ、横切を減らす。","폴라인 근처에서 범프를 연결하고 트래버스를 줄이세요.","Ligue bossas perto da linha de máxima pendente com menos travessias.")
p("Linked absorption near the fall line. No air score.","Absorption enchaînée près de la ligne de pente. Pas de note d’air.","Verkettete Absorption nahe der Falllinie. Keine Air-Wertung.","Absorción enlazada cerca de la línea de máxima pendiente. Sin puntuación de air.","Assorbimento concatenato vicino alla linea di massima pendenza. Niente punteggio air.","フォールライン近くの連続吸収。空中採点なし。","폴라인 근처 연결 흡수. 에어 채점 없음.","Absorção encadeada perto da linha de máxima pendente. Sem pontuação de air.")
p("Linked parallel turns with an even rhythm, a flex-and-extend move, and a pole touch at every edge change.",
  "Virages parallèles enchaînés, rythme régulier, flexion–extension, toucher de bâton à chaque changement de carre.",
  "Verkettete Parallelschwünge, gleichmäßiger Rhythmus, Beugen–Strecken, Stocktouch bei jedem Kantenwechsel.",
  "Curvas paralelas enlazadas, ritmo uniforme, flexión–extensión y toque de bastón en cada cambio de canto.",
  "Curve parallele concatenate, ritmo uniforme, flessione–estensione e tocco di bastoncino a ogni cambio di lama.",
  "連続パラレル：均等なリズム、蹲伸、毎回のエッジチェンジでポールタッチ。",
  "연결 패러렐 턴: 고른 리듬, 굴신, 매 엣지 체인지마다 폴 터치.",
  "Curvas paralelas encadeadas, ritmo uniforme, flexão–extensão e toque de bastão a cada mudança de canto.")
p("Linked short skids on parallel skis; mixed edge and skid is acceptable.",
  "Courts dérapages enchaînés en parallèle ; mélange carre/dérapage acceptable.",
  "Verkettete kurze Drifts parallel; Kante/Drift gemischt ist ok.",
  "Derrapes cortos enlazados en paralelo; mezcla canto/derrape aceptable.",
  "Derapate corte concatenate in parallelo; mix lama/derapata accettabile.",
  "パラレルでの短い連続スキッド。エッジとスキッドの混合は可。",
  "패러렐에서 짧은 연결 스키드. 엣지·스키드 혼합 가능.",
  "Derrapagens curtas encadeadas em paralelo; mistura canto/derrapagem aceitável.")
p("Linked turns","Virages enchaînés","Verkettete Schwünge","Curvas enlazadas","Curve concatenate","連続ターン","연결 턴","Curvas encadeadas")
p("Locked","Verrouillé","Gesperrt","Bloqueado","Bloccato","ロック","잠김","Bloqueado")
p("Locked because","Verrouillé parce que","Gesperrt weil","Bloqueado porque","Bloccato perché","ロック理由","잠긴 이유","Bloqueado porque")
p("Long-radius carve","Carving grand rayon","Carving langer Radius","Carving de radio largo","Carving a raggio lungo","ロングターン・カービング","롱턴 카빙","Carving de raio longo")
p("Look downhill","Regardez vers le bas de la pente","Blick talwärts","Mira hacia abajo","Guarda a valle","視線は山下へ","시선은 밸리 쪽","Olhe para baixo da pendente")

out = Path("locales/_ski_locale_fills/part02.json")
out.write_text(json.dumps(T, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("wrote", len(T), "->", out)
