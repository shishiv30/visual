# -*- coding: utf-8 -*-
import json
from pathlib import Path

def L(fr, de, es, it, ja, ko, pt):
    return dict(fr=fr, de=de, es=es, it=it, ja=ja, ko=ko, pt=pt)

T = {}

def p(en, fr, de, es, it, ja, ko, pt):
    T[en] = L(fr, de, es, it, ja, ko, pt)

p(
    "On a green run, stand across the hill, flatten both skis to slip, then edge to stop; ten repeats each way.",
    "Sur piste verte, placez-vous en travers, aplatissez les deux skis pour déraper, puis remettez les carres pour stopper ; dix fois dans chaque sens.",
    "Auf grüner Piste quer zum Hang stehen, beide Ski flachstellen zum Rutschen, dann kanten zum Stoppen; zehn Wiederholungen je Richtung.",
    "En pista verde, colócate de través, aplana ambos esquís para derrapar y canta para frenar; diez repeticiones a cada lado.",
    "Su pista verde, mettiti di traverso, appiattisci entrambi gli sci per derapare, poi rimetti le lame per fermarti; dieci ripetizioni per lato.",
    "緑斜面で斜面に対して横向きに立ち、両スキーをフラットにして横滑りし、エッジを立てて止まる。左右各10回。",
    "그린 슬로프에서 사면에 가로로 서고, 양 스키를 플랫하게 해 스키드한 뒤 엣지로 정지. 좌우 각 10회.",
    "Em pista verde, coloque-se de través, aplaine ambos os skis para derrapar e cante para parar; dez repetições para cada lado.",
)
p(
    "On a short steep section, pivot-slip eight times; link short turns only once the upper body stays quiet.",
    "Sur un court passage raide, faites huit pivot-slips ; n’enchaînez les virages courts que lorsque le haut du corps reste calme.",
    "Auf einem kurzen Steilabschnitt acht Pivot-Slips; kurze Schwünge erst verknüpfen, wenn der Oberkörper ruhig bleibt.",
    "En un tramo corto y empinado, ocho pivot-slips; enlaza virajes cortos solo cuando el tronco superior se mantenga quieto.",
    "Su un tratto corto e ripido, otto pivot-slip; concatena curve corte solo quando il busto resta quieto.",
    "短い急斜面でピボットスリップを8回。上体が静かになってからショートターンを繋ぐ。",
    "짧은 급경사에서 피벗 슬립 8회. 상체가 고요해진 뒤에만 숏턴을 연결.",
    "Num troço curto e íngreme, oito pivot-slips; encadeie curvas curtas só quando o tronco superior ficar quieto.",
)
p(
    "On land: athletic stance, rotate the femurs to turn the toes, keep the shoulders still.",
    "À terre : position athlétique, tournez les fémurs pour orienter les pieds, épaules immobiles.",
    "Am Boden: athletische Haltung, Femur drehen um die Zehen zu wenden, Schultern still.",
    "En seco: postura atlética, gira los fémures para orientar los pies, hombros quietos.",
    "A terra: postura atletica, ruota i femori per orientare i piedi, spalle ferme.",
    "陸上：アスレチックスタンスで大腿を回してつま先を向け、肩は動かさない。",
    "육상: 애슬레틱 스탠스, 대퇴를 돌려 발가락을 돌리고 어깨는 고정.",
    "Em terra: postura atlética, rode os fémures para orientar os pés, ombros quietos.",
)
p(
    "One cell per turn along the clip. Flagged turns are highlighted; click a turn to jump to it.",
    "Une case par virage le long du clip. Les virages signalés sont surlignés ; cliquez pour y aller.",
    "Eine Zelle pro Schwung entlang des Clips. Markierte Schwünge sind hervorgehoben; klicken zum Springen.",
    "Una celda por curva a lo largo del clip. Las curvas marcadas se resaltan; haz clic para saltar.",
    "Una cella per curva lungo la clip. Le curve segnalate sono evidenziate; clicca per andarci.",
    "クリップ上でターンごとに1セル。フラグ付きターンは強調表示；クリックでジャンプ。",
    "클립을 따라 턴당 한 칸. 표시된 턴이 강조되며, 클릭하면 해당 위치로 이동.",
    "Uma célula por curva ao longo do clipe. Curvas assinaladas ficam destacadas; clique para saltar.",
)
p(
    "One-ski / outside-leg drill",
    "Exercice un ski / jambe extérieure",
    "Ein-Ski- / Außenskibeine-Drill",
    "Ejercicio de un esquí / pierna exterior",
    "Drill a uno sci / gamba esterna",
    "ワンスキー／外足ドリル",
    "원스키 / 외측 다리 드릴",
    "Exercício de um ski / perna exterior",
)
p(
    "Only try boxes, rails, or jumps with a coach, a helmet, and a supervised park.",
    "N’essayez boxes, rails ou sauts qu’avec un moniteur, un casque et un snowpark encadré.",
    "Boxen, Rails oder Jumps nur mit Trainer, Helm und betreutem Park versuchen.",
    "Prueba boxes, rails o saltos solo con instructor, casco y park supervisado.",
    "Prova box, rail o salti solo con maestro, casco e park supervisionato.",
    "ボックス・レール・ジャンプはコーチ・ヘルメット・管理されたパークでのみ。",
    "박스·레일·점프는 코치·헬멧·감독되는 파크에서만.",
    "Experimente boxes, rails ou saltos só com instrutor, capacete e park supervisionado.",
)
p(
    "Only {count} turns were detected; film at least 8 linked turns for a rhythm score.",
    "Seuls {count} virages détectés ; filmez au moins 8 virages enchaînés pour un score de rythme.",
    "Nur {count} Schwünge erkannt; filme mindestens 8 verkettete Schwünge für eine Rhythmusnote.",
    "Solo se detectaron {count} curvas; filma al menos 8 curvas enlazadas para una puntuación de ritmo.",
    "Solo {count} curve rilevate; riprendi almeno 8 curve concatenate per un punteggio di ritmo.",
    "検出ターンは{count}のみ。リズム採点には連続ターンを8本以上撮影。",
    "감지된 턴은 {count}개뿐. 리듬 점수에는 연결 턴을 최소 8개 촬영.",
    "Apenas {count} curvas detetadas; filme pelo menos 8 curvas encadeadas para uma nota de ritmo.",
)
p(
    "Open the report on the player page to jump to this frame.",
    "Ouvrez le rapport sur la page lecteur pour aller à cette image.",
    "Öffne den Bericht auf der Player-Seite, um zu diesem Frame zu springen.",
    "Abre el informe en la página del reproductor para saltar a este fotograma.",
    "Apri il report nella pagina player per saltare a questo fotogramma.",
    "プレーヤー画面のレポートを開き、このフレームへジャンプ。",
    "플레이어 페이지의 리포트를 열어 이 프레임으로 이동.",
    "Abra o relatório na página do leitor para saltar para este fotograma.",
)
p(
    "Open the tails and edge to a stop; do not sit down.",
    "Ouvrez les talons et freinez sur les carres ; ne vous asseyez pas.",
    "Fersen öffnen und auf der Kante stoppen; nicht hinsetzen.",
    "Abre las colas y frena con el canto; no te sientes.",
    "Apri le code e ferma sulle lame; non sederti.",
    "テールを開きエッジで止まる。座り込まない。",
    "테일을 열고 엣지로 정지. 앉지 말 것.",
    "Abra as caudas e pare no canto; não se sente.",
)
p(
    "Open then close",
    "Ouvrir puis fermer",
    "Öffnen dann schließen",
    "Abrir y luego cerrar",
    "Apri poi chiudi",
    "開いてから閉じる",
    "열고 닫기",
    "Abrir e depois fechar",
)
p(
    "Ordered for your weakest metric first: {metric}",
    "Classé d’abord sur votre métrique la plus faible : {metric}",
    "Zuerst nach deiner schwächsten Metrik geordnet: {metric}",
    "Ordenado primero por tu métrica más débil: {metric}",
    "Ordinato prima per la metrica più debole: {metric}",
    "最も弱い指標を優先して並べ替え：{metric}",
    "가장 약한 지표 우선 정렬: {metric}",
    "Ordenado primeiro pela métrica mais fraca: {metric}",
)
p(
    "Out point must be after in point.",
    "Le point de sortie doit être après le point d’entrée.",
    "Out-Punkt muss nach dem In-Punkt liegen.",
    "El punto de salida debe ser posterior al de entrada.",
    "Il punto out deve essere dopo il punto in.",
    "アウト地点はイン地点より後にしてください。",
    "아웃 지점은 인 지점보다 뒤여야 합니다.",
    "O ponto de saída tem de ser depois do de entrada.",
)
p(
    "Outside-ski center of mass",
    "Centre de masse sur le ski extérieur",
    "Körperschwerpunkt auf dem Außenski",
    "Centro de masas sobre el esquí exterior",
    "Centro di massa sullo sci esterno",
    "外足スキーへの重心",
    "외측 스키 무게중심",
    "Centro de massa no ski exterior",
)
p(
    "Parallel-ski emergency stop; required braking skill before short skidded turns.",
    "Arrêt d’urgence en skis parallèles ; freinage obligatoire avant les virages courts en dérapage.",
    "Notstopp mit parallelen Skiern; nötige Bremskompetenz vor kurzen Drift-Schwüngen.",
    "Frenada de emergencia con esquís paralelos; habilidad de frenado requerida antes de virajes cortos derrapados.",
    "Arresto di emergenza a sci paralleli; frenata obbligatoria prima delle curve corte derapate.",
    "パラレル緊急停止。ショートスキッドターンの前に必須のブレーキ技術。",
    "패러렐 비상 정지. 숏 스키드 턴 전에 필수인 제동 기술.",
    "Paragem de emergência com skis paralelos; travagem obrigatória antes de curvas curtas derrapadas.",
)
p(
    "Park / jumps",
    "Park / sauts",
    "Park / Jumps",
    "Park / saltos",
    "Park / salti",
    "パーク／ジャンプ",
    "파크 / 점프",
    "Park / saltos",
)
p(
    "Park skiing",
    "Ski de park",
    "Parkfahren",
    "Esquí de park",
    "Sci da park",
    "パーク滑走",
    "파크 스키",
    "Ski de park",
)
p(
    "Passed this level. Choose a next level on the skill tree.",
    "Niveau validé. Choisissez le suivant dans l’arbre de compétences.",
    "Stufe bestanden. Wähle die nächste im Skill-Baum.",
    "Nivel aprobado. Elige el siguiente en el árbol de habilidades.",
    "Livello superato. Scegli il successivo nell’albero delle abilità.",
    "この段階に合格。スキルツリーで次の段階を選んでください。",
    "이 단계 통과. 스킬 트리에서 다음 단계를 선택하세요.",
    "Nível aprovado. Escolha o seguinte na árvore de competências.",
)
p(
    "Pick a branch, film your own skiing, and run your own practice cycle.",
    "Choisissez une branche, filmez votre ski et enchaînez votre cycle d’entraînement.",
    "Wähle einen Ast, filme dein Skifahren und durchlaufe deinen Übungszyklus.",
    "Elige una rama, filma tu esquí y recorre tu ciclo de práctica.",
    "Scegli un ramo, riprendi il tuo sci e fai il tuo ciclo di pratica.",
    "枝を選び、自分の滑りを撮り、練習サイクルを回す。",
    "가지를 고르고, 본인 스키를 촬영해 연습 사이클을 돌리세요.",
    "Escolha um ramo, filme o seu ski e percorra o seu ciclo de treino.",
)
p(
    "Pick the gentlest pitch; avoid ice and crowded runouts.",
    "Choisissez la pente la plus douce ; évitez la glace et les sorties encombrées.",
    "Wähle die flachste Neigung; Eis und volle Ausläufe meiden.",
    "Elige la pendiente más suave; evita hielo y salidas concurridas.",
    "Scegli la pendenza più dolce; evita ghiaccio e uscite affollate.",
    "いちばん緩い斜面を選ぶ。アイスと混雑したランアウトは避ける。",
    "가장 완만한 경사 선택. 아이스와 붐비는 런아웃은 피하세요.",
    "Escolha a pendente mais suave; evite gelo e saídas lotadas.",
)
p(
    "Pivot both skis under a quiet upper body, slip a short distance, then pivot back.",
    "Pivotez les deux skis sous un haut du corps calme, dérapez un peu, puis pivotez en sens inverse.",
    "Beide Ski unter ruhigem Oberkörper pivotieren, kurz rutschen, dann zurückpivotieren.",
    "Pivota ambos esquís bajo un tronco quieto, derrapa un tramo corto y pivota de vuelta.",
    "Pivotare entrambi gli sci sotto un busto quieto, derapare un breve tratto, poi pivotare indietro.",
    "静かな上体の下で両スキーをピボットし、少し横滑りしてから戻す。",
    "고요한 상체 아래 양 스키를 피벗하고, 짧게 스키드한 뒤 다시 피벗.",
    "Pivotar ambos os skis sob um tronco quieto, derrapar um pouco e pivotar de volta.",
)
p(
    "Pivot-slip on a steep pitch",
    "Pivot-slip sur pente raide",
    "Pivot-Slip auf steilem Hang",
    "Pivot-slip en pendiente empinada",
    "Pivot-slip su pendenza ripida",
    "急斜面でのピボットスリップ",
    "급경사 피벗 슬립",
    "Pivot-slip em pendente íngreme",
)
p(
    "Pole touch every turn",
    "Planté à chaque virage",
    "Stockeinsatz bei jedem Schwung",
    "Toque de bastón en cada curva",
    "Tocco di bastoncino a ogni curva",
    "毎ターンでポールタッチ",
    "매 턴 폴 터치",
    "Toque de bastão em cada curva",
)
p(
    "Pole touch per turn",
    "Planté par virage",
    "Stockeinsatz pro Schwung",
    "Toque de bastón por curva",
    "Tocco di bastoncino per curva",
    "ターンあたりのポールタッチ",
    "턴당 폴 터치",
    "Toque de bastão por curva",
)
p(
    "Pole touch timing",
    "Timing du planté",
    "Timing des Stockeinsatzes",
    "Timing del toque de bastón",
    "Timing del tocco di bastoncino",
    "ポールタッチのタイミング",
    "폴 터치 타이밍",
    "Timing do toque de bastão",
)
p(
    "Poles and hands",
    "Bâtons et mains",
    "Stöcke und Hände",
    "Bastones y manos",
    "Bastoncini e mani",
    "ポールと手",
    "폴과 손",
    "Bastões e mãos",
)
p(
    "Poses: {count}",
    "Poses : {count}",
    "Posen: {count}",
    "Poses: {count}",
    "Pose: {count}",
    "ポーズ: {count}",
    "자세: {count}",
    "Posturas: {count}",
)
p(
    "Possible stage",
    "Niveau possible",
    "Mögliche Stufe",
    "Nivel posible",
    "Livello possibile",
    "候補の段階",
    "가능 단계",
    "Nível possível",
)
p(
    "Possible stage — confidence is below the gate, so both candidates are shown.",
    "Niveau possible — confiance sous le seuil : les deux candidats sont affichés.",
    "Mögliche Stufe — Konfidenz unter dem Gate, daher beide Kandidaten angezeigt.",
    "Nivel posible — la confianza está bajo el umbral, así que se muestran ambos candidatos.",
    "Livello possibile — confidenza sotto la soglia: mostrati entrambi i candidati.",
    "候補段階——信頼度がゲート未満のため、候補を両方表示。",
    "가능 단계 — 신뢰도가 게이트 미만이라 후보를 둘 다 표시.",
    "Nível possível — confiança abaixo do limiar, por isso ambos os candidatos são mostrados.",
)
p(
    "Powder",
    "Poudreuse",
    "Powder",
    "Powder",
    "Powder",
    "パウダー",
    "파우더",
    "Powder",
)
p(
    "Powder and soft snow",
    "Poudreuse et neige souple",
    "Powder und weicher Schnee",
    "Powder y nieve blanda",
    "Powder e neve morbida",
    "パウダーと柔らかい雪",
    "파우더와 부드러운 눈",
    "Powder e neve macia",
)
p(
    "Practice inclination on blue before moving to red; drop to an easier pitch when form fades.",
    "Travaillez l’inclinaison sur bleue avant la rouge ; descendez en pente plus douce si la forme se dégrade.",
    "Neigung auf Blau üben, bevor Rot kommt; bei Formverlust auf leichteren Hang wechseln.",
    "Practica la inclinación en azul antes de pasar a roja; baja a una pendiente más fácil si la forma se pierde.",
    "Allena l’inclinazione sul blu prima del rosso; scendi a una pendenza più facile se la forma cala.",
    "赤に進む前に青でインクラインを練習。フォームが崩れたら緩い斜面へ戻す。",
    "레드로 가기 전 블루에서 인클리네이션 연습. 폼이 무너지면 쉬운 경사로.",
    "Pratique a inclinação no azul antes do vermelho; desça para uma pendente mais fácil se a forma cair.",
)
p(
    "Prefer fewer people and softer snow; shallower turns on ice.",
    "Préférez peu de monde et neige plus souple ; virages plus plats sur glace.",
    "Lieber weniger Leute und weicherer Schnee; flachere Schwünge auf Eis.",
    "Prefiere menos gente y nieve más blanda; curvas más planas en hielo.",
    "Preferisci poca gente e neve più morbida; curve più piatte sul ghiaccio.",
    "人が少なく柔らかい雪を優先。アイスでは浅めのターン。",
    "사람 적고 부드러운 눈 선호. 아이스에서는 얕은 턴.",
    "Prefira menos gente e neve mais macia; curvas mais planas no gelo.",
)
p(
    "Pressure peak in the turn",
    "Pic de pression dans le virage",
    "Druckspitze im Schwung",
    "Pico de presión en la curva",
    "Picco di pressione in curva",
    "ターン内の圧力ピーク",
    "턴 내 압력 피크",
    "Pico de pressão na curva",
)
p(
    "Pressure peaks in the shaping phase",
    "Pics de pression en phase de mise en forme",
    "Druckspitzen in der Formungsphase",
    "Picos de presión en la fase de forma",
    "Picchi di pressione nella fase di sagomatura",
    "シェイピング局面での圧力ピーク",
    "셰이핑 국면의 압력 피크",
    "Picos de pressão na fase de forma",
)
p(
    "Problem frame",
    "Image problème",
    "Problem-Frame",
    "Fotograma problemático",
    "Fotogramma problematico",
    "問題フレーム",
    "문제 프레임",
    "Fotograma problemático",
)
p(
    "Processing",
    "Traitement",
    "Verarbeitung",
    "Procesando",
    "Elaborazione",
    "処理中",
    "처리 중",
    "A processar",
)
p(
    "Profile",
    "Profil",
    "Profil",
    "Perfil",
    "Profilo",
    "プロフィール",
    "프로필",
    "Perfil",
)
p(
    "Profile view",
    "Vue de profil",
    "Seitenansicht",
    "Vista de perfil",
    "Vista di profilo",
    "プロフィール視点",
    "측면 뷰",
    "Vista de perfil",
)
p(
    "Progression rung — not judged from a clip.",
    "Échelon de progression — non jugé depuis un clip.",
    "Progressionsstufe — nicht aus einem Clip beurteilbar.",
    "Peldaño de progresión — no se juzga desde un clip.",
    "Gradino di progressione — non giudicabile da una clip.",
    "進行段階——クリップからは判定しない。",
    "진행 단계 — 클립으로 판정하지 않음.",
    "Degrau de progressão — não julgado a partir de um clipe.",
)
p(
    "Purpose",
    "Objectif",
    "Zweck",
    "Propósito",
    "Scopo",
    "目的",
    "목적",
    "Objetivo",
)
p(
    "Put the gear on, walk on the flat, glide a few metres, and get up after a fall.",
    "Enfilez le matériel, marchez à plat, glissez quelques mètres et relevez-vous après une chute.",
    "Ausrüstung anziehen, auf der Flachen gehen, ein paar Meter gleiten und nach einem Sturz aufstehen.",
    "Ponte el equipo, camina en llano, desliza unos metros y levántate tras una caída.",
    "Indossa l’attrezzatura, cammina in piano, scorri pochi metri e rialzati dopo una caduta.",
    "用具を着け、平坦地を歩き、数メートル滑り、転倒後に起き上がる。",
    "장비를 착용하고 평지를 걷고, 몇 미터 미끄러진 뒤 넘어지면 일어난다.",
    "Vista o equipamento, caminhe no plano, deslize alguns metros e levante-se após uma queda.",
)
p(
    "Quarter",
    "Quart",
    "Viertel",
    "Cuarto",
    "Quarto",
    "クォータ",
    "쿼터",
    "Quarto",
)
p(
    "Quick edge change on firm snow",
    "Changement de carre rapide sur neige dure",
    "Schneller Kantenwechsel auf hartem Schnee",
    "Cambio de canto rápido en nieve dura",
    "Cambio di lama rapido su neve dura",
    "硬い雪での素早いエッジチェンジ",
    "단단한 눈에서 빠른 엣지 체인지",
    "Mudança de canto rápida em neve dura",
)
p(
    "Quick left-right; no long traverse.",
    "Gauche-droite rapide ; pas de long travers.",
    "Schnell links-rechts; keine lange Traversale.",
    "Izquierda-derecha rápida; sin travesía larga.",
    "Sinistra-destra rapido; niente lunga traversata.",
    "素早い左右切替。長いトラバースはしない。",
    "빠른 좌우. 긴 트래버스 금지.",
    "Esquerda-direita rápida; sem travessia longa.",
)
p(
    "Quiet shoulders",
    "Épaules calmes",
    "Ruhige Schultern",
    "Hombros quietos",
    "Spalle quiete",
    "静かな肩",
    "고요한 어깨",
    "Ombros quietos",
)
p(
    "Quiet upper body",
    "Haut du corps calme",
    "Ruhiger Oberkörper",
    "Tronco superior quieto",
    "Busto quieto",
    "静かな上体",
    "고요한 상체",
    "Tronco superior quieto",
)
p(
    "Quiet, easy green run — master the wedge stop first.",
    "Piste verte calme et facile — maîtrisez d’abord l’arrêt en chasse-neige.",
    "Ruhige, leichte grüne Piste — zuerst den Pflug-Stopp beherrschen.",
    "Pista verde tranquila y fácil — domina primero la parada en cuña.",
    "Pista verde tranquilla e facile — padroneggia prima l’arresto a spazzaneve.",
    "静かでやさしい緑斜面——まずプルークストップを習得。",
    "조용하고 쉬운 그린 — 먼저 플루크 정지를 익히세요.",
    "Pista verde calma e fácil — domine primeiro a paragem em cunha.",
)
p(
    "Race",
    "Course",
    "Rennen",
    "Carrera",
    "Gara",
    "レース",
    "레이스",
    "Corrida",
)
p(
    "Race gates",
    "Portes de course",
    "Renn-Tore",
    "Puertas de carrera",
    "Porte di gara",
    "レースゲート",
    "레이스 게이트",
    "Portas de corrida",
)
p(
    "Re-film",
    "Refilmer",
    "Neu filmen",
    "Volver a filmar",
    "Riprendere",
    "撮り直し",
    "재촬영",
    "Voltar a filmar",
)
p(
    "Re-film this stage so its checkpoints can be measured.",
    "Refilmez ce niveau pour pouvoir mesurer ses points de contrôle.",
    "Filme diese Stufe neu, damit ihre Checkpoints messbar sind.",
    "Vuelve a filmar este nivel para poder medir sus checkpoints.",
    "Riprendi questo livello così da misurare i suoi checkpoint.",
    "この段階を撮り直し、チェックポイントを測定できるようにする。",
    "이 단계를 다시 촬영해 체크포인트를 측정할 수 있게 하세요.",
    "Volte a filmar este nível para poder medir os seus checkpoints.",
)
p(
    "Reach the standard on {name} to advance.",
    "Atteignez le standard sur {name} pour progresser.",
    "Erreiche den Standard bei {name}, um weiterzukommen.",
    "Alcanza el estándar en {name} para avanzar.",
    "Raggiungi lo standard su {name} per avanzare.",
    "{name}で基準に達すると次へ進みます。",
    "{name}에서 기준에 도달하면 진급합니다.",
    "Atinga o padrão em {name} para avançar.",
)
p(
    "Reach the standard on {name}, then move to {next}.",
    "Atteignez le standard sur {name}, puis passez à {next}.",
    "Erreiche den Standard bei {name}, dann weiter zu {next}.",
    "Alcanza el estándar en {name} y luego pasa a {next}.",
    "Raggiungi lo standard su {name}, poi passa a {next}.",
    "{name}で基準に達したら、{next}へ進む。",
    "{name}에서 기준에 도달한 뒤 {next}로 이동.",
    "Atinga o padrão em {name} e depois passe para {next}.",
)
p(
    "Read the terrain and pick a line in crud, cut-up snow and gladed trees. Inside the resort boundary only.",
    "Lisez le terrain et choisissez une ligne dans la neige bosselée, labourée et en forêt claire. Uniquement dans les limites de la station.",
    "Gelände lesen und eine Linie in Bruchschnee, zerfahrenem Schnee und lichten Bäumen wählen. Nur innerhalb der Gebietsgrenze.",
    "Lee el terreno y elige una línea en nieve irregular, pisada y claros de bosque. Solo dentro del dominio.",
    "Leggi il terreno e scegli una linea in neve irregolare, smossa e bosco rado. Solo dentro il comprensorio.",
    "地形を読み、クラッド・荒れ雪・疎林でラインを選ぶ。ゲレンデ境界内のみ。",
    "지형을 읽고 크러드·잘린 눈·숲 사이로 라인 선택. 리조트 경계 내에서만.",
    "Leia o terreno e escolha uma linha em neve irregular, cortada e bosque ralo. Só dentro do domínio.",
)
p(
    "Reanalyze",
    "Réanalyser",
    "Neu analysieren",
    "Reanalizar",
    "Rianalizza",
    "再分析",
    "재분석",
    "Reanalisar",
)
p(
    "Reason",
    "Raison",
    "Grund",
    "Motivo",
    "Motivo",
    "理由",
    "이유",
    "Motivo",
)
p(
    "Record",
    "Enregistrer",
    "Aufnehmen",
    "Grabar",
    "Registra",
    "録画",
    "녹화",
    "Gravar",
)
p(
    "Record at least one person box.",
    "Enregistrez au moins un cadre personne.",
    "Mindestens einen Personen-Rahmen aufnehmen.",
    "Graba al menos un cuadro de persona.",
    "Registra almeno un box persona.",
    "人物ボックスを少なくとも1つ記録。",
    "인물 박스를 최소 하나 기록하세요.",
    "Grave pelo menos uma caixa de pessoa.",
)
p(
    "Record box",
    "Cadre d’enregistrement",
    "Aufnahme-Rahmen",
    "Cuadro de grabación",
    "Box di registrazione",
    "記録ボックス",
    "기록 박스",
    "Caixa de gravação",
)
p(
    "Recorded boxes",
    "Cadres enregistrés",
    "Aufgenommene Rahmen",
    "Cuadros grabados",
    "Box registrati",
    "記録済みボックス",
    "기록된 박스",
    "Caixas gravadas",
)
p(
    "Red (steep groomed) run",
    "Piste rouge (damée raide)",
    "Rote (steile präparierte) Piste",
    "Pista roja (pisada empinada)",
    "Pista rossa (battuta ripida)",
    "赤（急な整備斜面）",
    "레드(급한 정비 슬로프)",
    "Pista vermelha (preparada íngreme)",
)
p(
    "Release both edges to slip sideways, then re-set them to stop; the torso keeps facing downhill.",
    "Relâchez les deux carres pour déraper de côté, puis remettez-les pour stopper ; le buste reste face à la pente.",
    "Beide Kanten lösen zum Seitwärtsrutschen, dann wieder setzen zum Stoppen; der Rumpf bleibt hangabwärts ausgerichtet.",
    "Suelta ambos cantos para derrapar de lado y vuélvelos a poner para parar; el tronco sigue mirando a la pendiente.",
    "Rilascia entrambe le lame per derapare di lato, poi rimettile per fermarti; il busto resta rivolto a valle.",
    "両エッジを外して横滑りし、再び立てて止まる。胴体は常に谷向き。",
    "양 엣지를 풀어 옆으로 스키드한 뒤 다시 세워 정지. 몸통은 계속 내리막 방향.",
    "Liberte ambos os cantos para derrapar de lado e volte a pô-los para parar; o tronco mantém-se virado à pendente.",
)
p(
    "Reliability {pct:.0f}%",
    "Fiabilité {pct:.0f}%",
    "Zuverlässigkeit {pct:.0f}%",
    "Fiabilidad {pct:.0f}%",
    "Affidabilità {pct:.0f}%",
    "信頼性 {pct:.0f}%",
    "신뢰도 {pct:.0f}%",
    "Fiabilidade {pct:.0f}%",
)
p(
    "Report",
    "Rapport",
    "Bericht",
    "Informe",
    "Report",
    "レポート",
    "리포트",
    "Relatório",
)
p(
    "Research notes (from knowledge base)",
    "Notes de recherche (base de connaissances)",
    "Forschungsnotizen (aus der Wissensbasis)",
    "Notas de investigación (base de conocimiento)",
    "Note di ricerca (dalla knowledge base)",
    "調査メモ（ナレッジベースより）",
    "조사 메모(지식 베이스)",
    "Notas de investigação (da base de conhecimento)",
)
p(
    "Retry",
    "Réessayer",
    "Erneut versuchen",
    "Reintentar",
    "Riprova",
    "再試行",
    "다시 시도",
    "Tentar novamente",
)
p(
    "Rhythm and turn shape",
    "Rythme et forme de virage",
    "Rhythmus und Schwungform",
    "Ritmo y forma de curva",
    "Ritmo e forma di curva",
    "リズムとターン形状",
    "리듬과 턴 형태",
    "Ritmo e forma de curva",
)
p(
    "Rhythm evenness",
    "Régularité du rythme",
    "Rhythmusgleichmäßigkeit",
    "Uniformidad del ritmo",
    "Uniformità del ritmo",
    "リズムの均一さ",
    "리듬 균일도",
    "Uniformidade do ritmo",
)
p(
    "Rhythm variation {cv:.0f}%",
    "Variation de rythme {cv:.0f}%",
    "Rhythmusvariation {cv:.0f}%",
    "Variación de ritmo {cv:.0f}%",
    "Variazione di ritmo {cv:.0f}%",
    "リズム変動 {cv:.0f}%",
    "리듬 변동 {cv:.0f}%",
    "Variação de ritmo {cv:.0f}%",
)
p(
    "Right",
    "Droite",
    "Rechts",
    "Derecha",
    "Destra",
    "右",
    "오른쪽",
    "Direita",
)
p(
    "Round bumps, an open line, visible troughs; do not force a black run.",
    "Bosses rondes, ligne ouverte, sillons visibles ; ne forcez pas une piste noire.",
    "Runde Buckel, offene Linie, sichtbare Rinnen; keine schwarze Piste erzwingen.",
    "Baches redondos, línea abierta, canales visibles; no fuerces una pista negra.",
    "Gobbe rotonde, linea aperta, canali visibili; non forzare una pista nera.",
    "丸いコブ、開いたライン、見える溝。無理に黒斜面にしない。",
    "둥근 범프, 열린 라인, 보이는 홈. 블랙을 억지로 타지 말 것.",
    "Bumps redondos, linha aberta, canais visíveis; não force uma pista negra.",
)
p(
    "Round long-radius turns",
    "Virages longs et ronds",
    "Runde Schwünge langer Radius",
    "Curvas redondas de radio largo",
    "Curve rotonde a raggio lungo",
    "丸いロングラジスターン",
    "둥근 롱 라디우스 턴",
    "Curvas redondas de raio longo",
)
p(
    "Round turns in soft snow",
    "Virages ronds en neige souple",
    "Runde Schwünge in weichem Schnee",
    "Curvas redondas en nieve blanda",
    "Curve rotonde in neve morbida",
    "柔らかい雪での丸いターン",
    "부드러운 눈에서 둥근 턴",
    "Curvas redondas em neve macia",
)
p(
    "Round, progressive long turns with parallel skis and inclination — coach heuristic, not a race carve score.",
    "Virages longs, ronds et progressifs en skis parallèles avec inclinaison — heuristique coach, pas un score de carving course.",
    "Runde, progressive Langschwünge mit parallelen Skiern und Neigung — Coach-Heuristik, keine Renn-Carving-Note.",
    "Curvas largas, redondas y progresivas con esquís paralelos e inclinación — heurística de coach, no una nota de carving de carrera.",
    "Curve lunghe, rotonde e progressive a sci paralleli con inclinazione — euristica coach, non un punteggio di carving da gara.",
    "パラレルとインクラインでの丸く漸進的なロングターン——コーチの目安でありレースカービング採点ではない。",
    "패러렐과 인클리네이션으로 둥글고 점진적인 롱턴 — 코치 휴리스틱이지 레이스 카빙 점수가 아님.",
    "Curvas longas, redondas e progressivas com skis paralelos e inclinação — heurística de coach, não uma nota de carving de corrida.",
)
p(
    "Round, shallow bumps; absorb in a straight line first.",
    "Bosses rondes et peu marquées ; absorbez d’abord en ligne droite.",
    "Runde, flache Buckel; zuerst in der Falllinie absorbieren.",
    "Baches redondos y poco profundos; absorbe primero en línea recta.",
    "Gobbe rotonde e poco profonde; assorbi prima in linea retta.",
    "丸く浅いコブ。まず直進で吸収。",
    "둥글고 얕은 범프. 먼저 직선으로 흡수.",
    "Bumps redondos e pouco profundos; absorva primeiro em linha reta.",
)
p(
    "Runner-up",
    "Second",
    "Zweiter",
    "Segundo",
    "Secondo",
    "次点",
    "차점",
    "Segundo",
)
p(
    "Safety",
    "Sécurité",
    "Sicherheit",
    "Seguridad",
    "Sicurezza",
    "安全",
    "안전",
    "Segurança",
)
p(
    "Saved profile",
    "Profil enregistré",
    "Gespeichertes Profil",
    "Perfil guardado",
    "Profilo salvato",
    "保存済みプロフィール",
    "저장된 프로필",
    "Perfil guardado",
)
p(
    "Scorable from the clip",
    "Notable depuis le clip",
    "Aus dem Clip bewertbar",
    "Puntuable desde el clip",
    "Valutabile dalla clip",
    "クリップから採点可能",
    "클립으로 채점 가능",
    "Pontuável a partir do clipe",
)

out = Path("locales/_ski_locale_fills/part04.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(T, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("wrote", len(T), "->", out)
