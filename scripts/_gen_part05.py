# -*- coding: utf-8 -*-
import json
from pathlib import Path

def L(fr, de, es, it, ja, ko, pt):
    return dict(fr=fr, de=de, es=es, it=it, ja=ja, ko=ko, pt=pt)

T = {}

def p(en, fr, de, es, it, ja, ko, pt):
    T[en] = L(fr, de, es, it, ja, ko, pt)

p("Scoring rules (from knowledge base)",
  "Règles de notation (base de connaissances)",
  "Bewertungsregeln (Wissensbasis)",
  "Reglas de puntuación (base de conocimiento)",
  "Regole di valutazione (base di conoscenza)",
  "採点ルール（ナレッジベース）",
  "채점 규칙(지식 베이스)",
  "Regras de pontuação (base de conhecimento)")

p("Select the person",
  "Sélectionner la personne",
  "Person auswählen",
  "Seleccionar a la persona",
  "Seleziona la persona",
  "人物を選択",
  "사람 선택",
  "Selecionar a pessoa")

p("Separated by",
  "Séparés par",
  "Getrennt durch",
  "Separados por",
  "Separati da",
  "区切り",
  "구분",
  "Separados por")

p("Session plan for this stage",
  "Plan de séance pour ce niveau",
  "Sitzungsplan für diese Stufe",
  "Plan de sesión para este nivel",
  "Piano di sessione per questo livello",
  "この段階のセッション計画",
  "이 단계의 세션 계획",
  "Plano de sessão para este nível")

p("Set aside because",
  "Mis de côté parce que",
  "Zurückgestellt weil",
  "Aplazado porque",
  "Messo da parte perché",
  "保留理由",
  "보류 이유",
  "Deixado de lado porque")

p("Set the edge above the fall line so the ski grips before it points down the hill.",
  "Posez la carre avant la ligne de pente pour que le ski accroche avant de viser la vallée.",
  "Setze die Kante oberhalb der Falllinie, damit der Ski greift, bevor er talwärts zeigt.",
  "Planta el canto antes de la línea de máxima pendiente para que el esquí agarre antes de apuntar valle abajo.",
  "Imposta la lama prima della linea di massima pendenza così lo sci morde prima di puntare a valle.",
  "フォールラインの手前でエッジを立て、板が谷を向く前にグリップさせる。",
  "폴라인 앞에서 엣지를 세워, 스키가 아래로 향하기 전에 잡아먹게 하세요.",
  "Coloque o canto antes da linha de máxima pendente para o ski agarrar antes de apontar para o vale.")

p("Sets of 8–12 bumps; stop when form fades.",
  "Séries de 8–12 bosses ; arrêtez dès que la forme se dégrade.",
  "Sätze zu 8–12 Buckeln; stoppen, wenn die Form nachlässt.",
  "Series de 8–12 baches; para cuando la forma se degrada.",
  "Serie da 8–12 gobbe; fermati quando la forma cala.",
  "8–12バンプを1セット。フォームが崩れたら中断。",
  "8–12개 범프를 한 세트; 폼이 무너지면 중단.",
  "Séries de 8–12 bossas; pare quando a forma se degrada.")

p("Setup",
  "Réglages",
  "Setup",
  "Configuración",
  "Setup",
  "セットアップ",
  "설정",
  "Configuração")

p("Sex is used only for fit guidance and the injury note; it never changes a score.",
  "Le sexe sert uniquement au conseil d’équipement et à la note blessure ; il ne modifie jamais un score.",
  "Geschlecht nur für Passform-Hinweise und die Verletzungsnotiz; es ändert nie eine Bewertung.",
  "El sexo solo sirve para orientación de talla y la nota de lesión; nunca cambia una puntuación.",
  "Il sesso serve solo per guida alla vestibilità e alla nota infortunio; non cambia mai un punteggio.",
  "性別はフィッティング案内とケガ注意のみに使い、得点には影響しません。",
  "성별은 피팅 안내와 부상 메모에만 쓰이며 점수를 바꾸지 않습니다.",
  "O sexo serve só para orientação de ajuste e a nota de lesão; nunca altera uma pontuação.")

p("Shallow C-turns while the wedge still brakes; load the outside ski.",
  "Virages en C peu marqués tant que le chasse-neige freine encore ; chargez le ski extérieur.",
  "Flache C-Schwünge, solange der Pflug noch bremst; Außenski belasten.",
  "Curvas en C suaves mientras la cuña aún frena; carga el esquí exterior.",
  "Curve a C poco pronunciate finché lo spazzaneve frena ancora; carica lo sci esterno.",
  "プルークがまだブレーキできる浅いCターン。外側板に荷重。",
  "플루크가 아직 제동하는 얕은 C턴; 바깥쪽 스키에 하중.",
  "Curvas em C suaves enquanto a cunha ainda trava; carregue o ski exterior.")

p("Shallow C-turns; hip internal rotation steers; the wedge stays.",
  "Virages en C peu marqués ; la rotation interne de hanche oriente ; le chasse-neige reste.",
  "Flache C-Schwünge; Innenrotation der Hüfte steuert; der Pflug bleibt.",
  "Curvas en C suaves; la rotación interna de cadera dirige; la cuña se mantiene.",
  "Curve a C poco pronunciate; la rotazione interna dell’anca guida; lo spazzaneve resta.",
  "浅いCターン。股関節内旋で舵取り、プルークは残す。",
  "얕은 C턴; 고관절 내회전으로 조향; 플루크 유지.",
  "Curvas em C suaves; a rotação interna da anca dirige; a cunha mantém-se.")

p("Shallow wedge C-turns",
  "Virages en C en chasse-neige peu marqué",
  "Flache Pflug-C-Schwünge",
  "Curvas en C en cuña suave",
  "Curve a C a spazzaneve poco pronunciato",
  "浅いプルークのCターン",
  "얕은 플루크 C턴",
  "Curvas em C em cunha suave")

p("Share",
  "Partager",
  "Teilen",
  "Compartir",
  "Condividi",
  "共有",
  "공유",
  "Partilhar")

p("Show skis",
  "Afficher les skis",
  "Ski anzeigen",
  "Mostrar esquís",
  "Mostra sci",
  "スキーを表示",
  "스키 표시",
  "Mostrar skis")

p("Shin angle",
  "Angle de tibia",
  "Schienbeinwinkel",
  "Ángulo de espinilla",
  "Angolo di tibia",
  "スネ角",
  "정강이 각도",
  "Ângulo da canela")

p("Short skidded turns",
  "Virages courts dérapés",
  "Kurze Driftenschwünge",
  "Curvas cortas derrapadas",
  "Curve corte derapate",
  "ショートスキッドターン",
  "숏 스키드 턴",
  "Curvas curtas derrapadas")

p("Short skidded-turn rhythm",
  "Rythme de virages courts dérapés",
  "Rhythmus kurzer Driftenschwünge",
  "Ritmo de curvas cortas derrapadas",
  "Ritmo di curve corte derapate",
  "ショートスキッドのリズム",
  "숏 스키드 턴 리듬",
  "Ritmo de curvas curtas derrapadas")

p("Short turns on a steep pitch: the upper body faces down the fall line and turn shape controls the speed.",
  "Virages courts en pente raide : le haut du corps face à la ligne de pente, la forme du virage gère la vitesse.",
  "Kurzschwünge am Steilen: Oberkörper zur Falllinie, Tempo über die Schwungform.",
  "Curvas cortas en pendiente fuerte: el tronco mira la línea de máxima pendiente y la forma de la curva controla la velocidad.",
  "Curve corte su pendio ripido: il busto guarda la linea di massima pendenza e la forma della curva regola la velocità.",
  "急斜面のショートターン：上体はフォールライン向き、速度はターン形で制御。",
  "급한 슬로프의 숏턴: 상체는 폴라인 방향, 속도는 턴 형태로 제어.",
  "Curvas curtas em pendente forte: o tronco enfrenta a linha de máxima pendente e a forma da curva controla a velocidade.")

p("Short-carve cadence",
  "Cadence de carving court",
  "Kurzcarve-Kadenz",
  "Cadencia de carving corto",
  "Cadenza di carving corto",
  "ショートカービングのリズム",
  "숏 카빙 케이던스",
  "Cadência de carving curto")

p("Short-radius carve",
  "Carving petit rayon",
  "Carving kurzer Radius",
  "Carving de radio corto",
  "Carving a raggio corto",
  "ショートラジウス・カービング",
  "숏 라디우스 카빙",
  "Carving de raio curto")

p("Short-radius carve cadence",
  "Cadence de carving petit rayon",
  "Kadenz Carving kurzer Radius",
  "Cadencia de carving de radio corto",
  "Cadenza di carving a raggio corto",
  "ショートラジウス・カービングのリズム",
  "숏 라디우스 카빙 케이던스",
  "Cadência de carving de raio curto")

p("Short-radius skids for speed control; hockey stop required. Then moguls.",
  "Dérapages petit rayon pour freiner ; hockey stop obligatoire. Ensuite les bosses.",
  "Kurzradius-Drifts zur Tempokontrolle; Hockey-Stopp Pflicht. Dann Buckel.",
  "Derrapes de radio corto para controlar velocidad; hockey stop obligatorio. Luego baches.",
  "Derapate a raggio corto per controllare la velocità; hockey stop obbligatorio. Poi le gobbe.",
  "ショートラジウス・スキッドで速度制御；ホッケーストップ必須。その後モーグル。",
  "숏 라디우스 스키드로 속도 제어; 하키 스톱 필수. 이후 모글.",
  "Derrapagens de raio curto para controlar velocidade; hockey stop obrigatório. Depois moguls.")

p("Short-turn cadence",
  "Cadence de virage court",
  "Kurzschwung-Kadenz",
  "Cadencia de curva corta",
  "Cadenza di curva corta",
  "ショートターンのリズム",
  "숏턴 케이던스",
  "Cadência de curva curta")

p("Shorten the legs at the crest, lengthen in the trough; stay on snow, do not jump.",
  "Raccourcissez les jambes au sommet, allongez dans le creux ; restez sur la neige, ne sautez pas.",
  "Beine auf dem Buckelkamm verkürzen, in der Mulde verlängern; Schnee halten, nicht springen.",
  "Acorta las piernas en la cresta, alarga en el valle; quédate en la nieve, no saltes.",
  "Accorcia le gambe sulla cresta, allunga nel canale; resta sulla neve, non saltare.",
  "頂で脚を縮め、谷で伸ばす。雪面を離れず、ジャンプしない。",
  "정상에서 다리를 줄이고 골에서 늘리세요; 설면에 붙고 점프하지 마세요.",
  "Encurte as pernas na crista, alongue no vale; fique na neve, não salte.")

p("Shorten the radius only after long-radius inclination works.",
  "Raccourcissez le rayon seulement quand l’inclinaison grand rayon fonctionne.",
  "Radius erst verkürzen, wenn die Neigung im langen Radius sitzt.",
  "Acorta el radio solo cuando la inclinación de radio largo funciona.",
  "Accorcia il raggio solo quando l’inclinazione a raggio lungo funziona.",
  "ロングの傾動が決まってから半径を短くする。",
  "롱 라디우스 기울기가 되면 그다음에야 반경을 줄이세요.",
  "Encurte o raio só depois de a inclinação de raio longo funcionar.")

p("Show you can stop on command with parallel skis (both directions).",
  "Montrez que vous savez vous arrêter sur ordre en skis parallèles (les deux sens).",
  "Zeige, dass du auf Kommando parallel stoppen kannst (beide Richtungen).",
  "Demuestra que puedes parar a comando con esquís paralelos (ambos sentidos).",
  "Mostra di saper fermarti su comando con sci paralleli (entrambe le direzioni).",
  "指示でパラレル停止できることを左右両方向で示す。",
  "지시하면 패러렐로 멈출 수 있음을 양쪽 방향으로 보이세요.",
  "Mostre que consegue parar a comando com skis paralelos (ambos os sentidos).")

p("Side or rear-quarter, whole run, little occlusion.",
  "De côté ou trois-quarts arrière, course entière, peu d’occlusion.",
  "Seitlich oder hintere Schrägansicht, ganze Abfahrt, wenig Verdeckung.",
  "Lateral o tres cuartos traseros, carrera completa, poca oclusión.",
  "Laterale o tre quarti posteriori, discesa intera, poca occlusione.",
  "側面または斜め後方、全滑走、遮蔽は少なく。",
  "측면 또는 후사분면, 전체 활주, 가림 적게.",
  "Lateral ou três quartos traseiros, descida completa, pouca oclusão.")

p("Sideslip and edge release",
  "Dérapage latéral et relâchement de carre",
  "Seitengleiten und Kantenlösung",
  "Derrape lateral y liberación de canto",
  "Derapata laterale e rilascio lama",
  "サイドスリップとエッジ解放",
  "사이드슬립과 엣지 릴리스",
  "Derrapagem lateral e libertação de canto")

p("Single-leg strength for the christie close and carve outside ski.",
  "Force unilatérale pour la fermeture christiana et le ski extérieur en carving.",
  "Einbein-Kraft für den Christie-Schluss und den Carving-Außenski.",
  "Fuerza a una pierna para el cierre christie y el esquí exterior en carving.",
  "Forza monopodalica per la chiusura christie e lo sci esterno in carving.",
  "クリスティー収束とカービング外側板のための片脚筋力。",
  "크리스티 수각과 카빙 바깥 스키를 위한 한발 근력.",
  "Força unilateral para o fecho christie e o ski exterior em carving.")

p("Single-mogul absorption",
  "Absorption d’une bosse",
  "Einzelbuckel-Absorption",
  "Absorción de un solo bache",
  "Assorbimento di una gobba",
  "単一モーグル吸収",
  "단일 모글 흡수",
  "Absorção de um mogul")

p("Six large C-turns on a moderate pitch; longer outside leg.",
  "Six grands virages en C sur pente modérée ; jambe extérieure plus longue.",
  "Sechs große C-Schwünge auf mäßiger Piste; äußeres Bein länger.",
  "Seis grandes curvas en C en pendiente moderada; pierna exterior más larga.",
  "Sei grandi curve a C su pendio moderato; gamba esterna più lunga.",
  "中斜面で大きなCターンを6回。外側脚を長く。",
  "중간 슬로프에서 큰 C턴 6회; 바깥쪽 다리를 더 길게.",
  "Seis grandes curvas em C em pendente moderada; perna exterior mais longa.")

p("Six long turns on firm blue groomers; shorten the radius only while the track stays clean.",
  "Six longs virages sur bleues damées fermes ; raccourcissez le rayon seulement tant que la trace reste nette.",
  "Sechs lange Schwünge auf festen blauen Pisten; Radius nur verkürzen, solange die Spur sauber bleibt.",
  "Seis curvas largas en azules pisadas firmes; acorta el radio solo mientras la huella siga limpia.",
  "Sei curve lunghe su blu battute compatte; accorcia il raggio solo finché la traccia resta pulita.",
  "固い青の整地でロングターン6本。跡がきれいな範囲でのみ半径を短く。",
  "단단한 블루 정비면에서 롱턴 6회; 자국이 깨끗할 때만 반경을 줄이세요.",
  "Seis curvas longas em azuis preparadas firmes; encurte o raio só enquanto o rasto se mantém limpo.")

p("Six traverses per side; put the ski down if you wobble.",
  "Six traversées par côté ; reposez le ski si vous vacillez.",
  "Sechs Quergänge je Seite; Ski absetzen, wenn du wackelst.",
  "Seis travesías por lado; baja el esquí si te tambaleas.",
  "Sei diagonali per lato; appoggia lo sci se barcolli.",
  "片側6本のトラバース。ぐらついたら板を下ろす。",
  "쪽당 트래버스 6회; 흔들리면 스키를 내리세요.",
  "Seis travessias por lado; baixe o ski se oscilar.")

p("Skeleton quality",
  "Qualité du squelette",
  "Skelettqualität",
  "Calidad del esqueleto",
  "Qualità dello scheletro",
  "スケルトン品質",
  "스켈레톤 품질",
  "Qualidade do esqueleto")

p("Ski length",
  "Longueur de ski",
  "Skilänge",
  "Longitud del esquí",
  "Lunghezza sci",
  "スキー長",
  "스키 길이",
  "Comprimento do ski")

p("Ski length band: {low}-{high} cm",
  "Plage de longueur de ski : {low}-{high} cm",
  "Skilängenband: {low}-{high} cm",
  "Rango de longitud de esquí: {low}-{high} cm",
  "Fascia lunghezza sci: {low}-{high} cm",
  "スキー長帯: {low}-{high} cm",
  "스키 길이 대역: {low}-{high} cm",
  "Faixa de comprimento do ski: {low}-{high} cm")

p("Ski label saved",
  "Étiquette de ski enregistrée",
  "Ski-Label gespeichert",
  "Etiqueta de esquí guardada",
  "Etichetta sci salvata",
  "スキーラベルを保存しました",
  "스키 라벨 저장됨",
  "Etiqueta de ski guardada")

p("Skill tree",
  "Arbre de compétences",
  "Skill-Baum",
  "Árbol de habilidades",
  "Albero delle skill",
  "スキルツリー",
  "스킬 트리",
  "Árvore de competências")

p("Slightly lower in the turn; elastic knees.",
  "Un peu plus bas dans le virage ; genoux élastiques.",
  "Im Schwung etwas tiefer; elastische Knie.",
  "Un poco más bajo en la curva; rodillas elásticas.",
  "Un po’ più basso in curva; ginocchia elastiche.",
  "ターン中はやや低く。膝は弾力的に。",
  "턴 중 조금 낮게; 탄성 있는 무릎.",
  "Um pouco mais baixo na curva; joelhos elásticos.")

p("Slip down and across, forward then back, with the torso facing downhill.",
  "Glissez vers le bas et en travers, avant puis arrière, torse face à la vallée.",
  "Talwärts und quer gleiten, vor und zurück, Rumpf talwärts.",
  "Desliza abajo y al través, adelante y atrás, con el tronco mirando valle abajo.",
  "Scivola in basso e di traverso, avanti poi indietro, busto rivolto a valle.",
  "下方向と横切に滑らせ、前後へ。胴は谷向きのまま。",
  "아래로·가로로 미끄러지며 앞뒤로; 몸통은 계곡 방향.",
  "Deslize para baixo e ao atravessar, frente e depois atrás, com o tronco virado para o vale.")

p("Slope",
  "Pente",
  "Hangneigung",
  "Pendiente",
  "Pendenza",
  "斜度",
  "경사",
  "Pendente")

p("Slope band",
  "Plage de pente",
  "Neigungsband",
  "Rango de pendiente",
  "Fascia di pendenza",
  "斜度帯",
  "경사 대역",
  "Faixa de pendente")

p("Slush",
  "Soupe",
  "Sulz",
  "Nieve mojada",
  "Neve bagnata",
  "シャーベット雪",
  "슬러시",
  "Neve molhada")

p("Snow and slope are optional — leave them at not sure and the report still runs.",
  "Neige et pente sont optionnels — laissez « pas sûr », le rapport s’exécute quand même.",
  "Schnee und Neigung sind optional — bei „unsicher“ läuft der Bericht trotzdem.",
  "Nieve y pendiente son opcionales — déjalos en no seguro y el informe se genera igual.",
  "Neve e pendenza sono opzionali — lasciali su non sicuro e il report parte lo stesso.",
  "雪質と斜度は任意——「不明」のままでもレポートは生成されます。",
  "설질과 경사는 선택 — 「잘 모르겠음」으로 둬도 리포트는 생성됩니다.",
  "Neve e pendente são opcionais — deixe em «não tenho a certeza» e o relatório corre na mesma.")

p("Snow surface",
  "Surface de neige",
  "Schneeoberfläche",
  "Superficie de nieve",
  "Superficie nevosa",
  "雪面",
  "설면",
  "Superfície de neve")

p("Soft",
  "Souple",
  "Weich",
  "Blando",
  "Morbido",
  "柔らかい",
  "부드러움",
  "Macio")

p("Soft ankles, knees, and hips; center of mass over mid-foot.",
  "Chevilles, genoux et hanches souples ; centre de masse sur le mi-pied.",
  "Weiche Knöchel, Knie und Hüften; Masseschwerpunkt über der Fußmitte.",
  "Tobillos, rodillas y caderas blandos; centro de masa sobre el mediopié.",
  "Caviglie, ginocchia e anche morbide; baricentro sul mediopiede.",
  "足首・膝・股関節を柔らかく。重心は足中部の上。",
  "발목·무릎·고관절을 부드럽게; 무게중심은 발 중앙 위.",
  "Tornozelos, joelhos e ancas macios; centro de massa sobre o médio-pé.")

p("Soft knees and ankles",
  "Genoux et chevilles souples",
  "Weiche Knie und Knöchel",
  "Rodillas y tobillos blandos",
  "Ginocchia e caviglie morbide",
  "柔らかい膝と足首",
  "부드러운 무릎과 발목",
  "Joelhos e tornozelos macios")

p("Soft snow",
  "Neige souple",
  "Weicher Schnee",
  "Nieve blanda",
  "Neve morbida",
  "柔らかい雪",
  "부드러운 눈",
  "Neve macia")

p("Soft, ungroomed snow just off a marked run; stay inside the resort boundary.",
  "Neige souple non damée juste hors piste balisée ; restez dans les limites de la station.",
  "Weicher, unpräparierter Schnee direkt neben der markierten Piste; im Gebietsgrenze bleiben.",
  "Nieve blanda sin pisar justo fuera de una pista marcada; quédate dentro del dominio.",
  "Neve morbida non battuta appena fuori da una pista segnata; resta nel comprensorio.",
  "マークされたコース脇の未圧雪の柔らかい雪。ゲレンデ境界内に留まる。",
  "표시 슬로프 바로 옆의 비정비 부드러운 눈; 리조트 경계 안에 머무르세요.",
  "Neve macia não preparada logo ao lado de uma pista marcada; fique dentro do domínio.")

p("Some checkpoints for this stage could not be measured in this clip.",
  "Certains points de contrôle de ce niveau n’ont pas pu être mesurés dans ce clip.",
  "Einige Checkpoints dieser Stufe konnten in diesem Clip nicht gemessen werden.",
  "Algunos checkpoints de este nivel no se pudieron medir en este clip.",
  "Alcuni checkpoint di questo livello non sono misurabili in questa clip.",
  "この段階の一部チェックポイントはこのクリップで測定できませんでした。",
  "이 단계의 일부 체크포인트를 이 클립에서 측정하지 못했습니다.",
  "Alguns checkpoints deste nível não puderam ser medidos neste clipe.")

p("Specialization and self-coaching",
  "Spécialisation et auto-coaching",
  "Spezialisierung und Selbstcoaching",
  "Especialización y autoentrenamiento",
  "Specializzazione e auto-coaching",
  "専門化とセルフコーチング",
  "전문화와 셀프 코칭",
  "Especialização e auto-coaching")

p("Speed",
  "Vitesse",
  "Tempo",
  "Velocidad",
  "Velocità",
  "スピード",
  "속도",
  "Velocidade")

p("Stop labeling skis",
  "Arrêter d’étiqueter les skis",
  "Ski-Labeln beenden",
  "Dejar de etiquetar esquís",
  "Interrompi etichettatura sci",
  "スキーのラベリングを停止",
  "스키 라벨링 중지",
  "Parar de etiquetar skis")

p("Squats and split squats",
  "Squats et fentes",
  "Kniebeugen und Ausfallschritte",
  "Sentadillas y zancadas",
  "Squat e affondi",
  "スクワットとスプリットスクワット",
  "스쿼트와 스플릿 스쿼트",
  "Agachamentos e lunges")

p("Stability",
  "Stabilité",
  "Stabilität",
  "Estabilidad",
  "Stabilità",
  "安定性",
  "안정성",
  "Estabilidade")

p("Stability over time (time \u00d7 frame score)",
  "Stabilité dans le temps (temps \u00d7 score d’image)",
  "Stabilität über die Zeit (Zeit \u00d7 Frame-Score)",
  "Estabilidad en el tiempo (tiempo \u00d7 puntuación de fotograma)",
  "Stabilità nel tempo (tempo \u00d7 punteggio frame)",
  "時間経過の安定性（時間 \u00d7 フレーム得点）",
  "시간 안정성(시간 \u00d7 프레임 점수)",
  "Estabilidade ao longo do tempo (tempo \u00d7 pontuação de fotograma)")

p("Stable follow-cam, one skier, side or rear-quarter.",
  "Caméra en suivi stable, un skieur, de côté ou trois-quarts arrière.",
  "Stabile Follow-Cam, ein Skifahrer, seitlich oder hintere Schrägansicht.",
  "Cámara en seguimiento estable, un esquiador, lateral o tres cuartos traseros.",
  "Camera a seguire stabile, un sciatore, laterale o tre quarti posteriori.",
  "安定したフォロー撮影、スキーヤー1人、側面または斜め後方。",
  "안정적인 팔로우 촬영, 스키어 1명, 측면 또는 후사분면.",
  "Câmara a seguir estável, um esquiador, lateral ou três quartos traseiros.")

p("Stage",
  "Niveau",
  "Stufe",
  "Nivel",
  "Livello",
  "段階",
  "단계",
  "Nível")

p("Stage cannot be judged when the shot is unstable, occluded, or out of curriculum scope.",
  "Le niveau ne peut pas être jugé si le plan est instable, occulté ou hors programme.",
  "Stufe nicht beurteilbar bei wackligem, verdecktem oder lehrplanfremdem Material.",
  "El nivel no se puede juzgar si el plano es inestable, ocluido o fuera del currículo.",
  "Il livello non è giudicabile se l’inquadratura è instabile, occlusa o fuori curriculum.",
  "映像が不安定・遮蔽・カリキュラム外のときは段階を判定できません。",
  "촬영이 불안정·가림·커리큘럼 범위 밖이면 단계를 판정할 수 없습니다.",
  "O nível não pode ser julgado se o plano for instável, ocluído ou fora do currículo.")

p("Stage focus",
  "Focus du niveau",
  "Stufenfokus",
  "Enfoque del nivel",
  "Focus del livello",
  "段階の焦点",
  "단계 초점",
  "Foco do nível")

p("Stage tutorial",
  "Tutoriel du niveau",
  "Stufen-Tutorial",
  "Tutorial del nivel",
  "Tutorial del livello",
  "段階チュートリアル",
  "단계 튜토리얼",
  "Tutorial do nível")

p("Stance and balance",
  "Position et équilibre",
  "Stand und Balance",
  "Postura y equilibrio",
  "Assetto ed equilibrio",
  "スタンスとバランス",
  "스탠스와 균형",
  "Postura e equilíbrio")

p("Stance width",
  "Écartement",
  "Standbreite",
  "Ancho de base",
  "Larghezza di base",
  "スタンス幅",
  "스탠스 폭",
  "Largura de base")

p("Stance width change",
  "Variation d’écartement",
  "Standbreitenwechsel",
  "Cambio de ancho de base",
  "Variazione di base",
  "スタンス幅の変化",
  "스탠스 폭 변화",
  "Variação da largura de base")

p("Stance width varies; not a locked wedge the whole turn.",
  "L’écartement varie ; ce n’est pas un chasse-neige figé tout le virage.",
  "Standbreite variiert; kein starrer Pflug den ganzen Schwung.",
  "El ancho de base varía; no es una cuña bloqueada todo el giro.",
  "La base varia; non è uno spazzaneve bloccato per tutta la curva.",
  "スタンス幅は変化する。ターン全体で固まったプルークではない。",
  "스탠스 폭이 변함; 턴 내내 고정된 플루크가 아님.",
  "A largura de base varia; não é uma cunha travada em toda a curva.")

p("Standard",
  "Critère",
  "Standard",
  "Estándar",
  "Standard",
  "基準",
  "기준",
  "Padrão")

p("Standard: a clean, narrow track on hardpack with no scraped-out tail.",
  "Critère : trace nette et étroite sur neige dure, sans queue raclée.",
  "Standard: saubere, schmale Spur auf Hartschnee ohne ausgekratztes Heck.",
  "Estándar: huella limpia y estrecha en nieve dura, sin cola raspada.",
  "Standard: traccia pulita e stretta su neve dura, senza coda raschiata.",
  "基準：硬雪に細くきれいな軌跡、テールの擦過なし。",
  "기준: 하드팩에 깨끗하고 좁은 자국, 테일 스크레이프 없음.",
  "Padrão: rasto limpo e estreito em neve dura, sem cauda raspada.")

p("Standard: a clear edge change, not an upright scrape.",
  "Critère : un changement de carre net, pas un raclage debout.",
  "Standard: klarer Kantenwechsel, kein aufrechtes Schaben.",
  "Estándar: cambio de canto claro, no un raspado erguido.",
  "Standard: cambio lama netto, non una raschiata eretta.",
  "基準：はっきりしたエッジチェンジで、直立の擦過ではない。",
  "기준: 명확한 엣지 체인지, 직립 스크레이프 아님.",
  "Padrão: mudança de canto clara, não uma raspagem erecta.")

p("Standard: both skis surface together; no single-ski dive.",
  "Critère : les deux skis remontent ensemble ; pas de plongée sur un ski.",
  "Standard: beide Ski schwimmen zusammen auf; kein Eintauchen eines Skis.",
  "Estándar: ambos esquís afloran juntos; sin hundirse uno solo.",
  "Standard: entrambi gli sci affiorano insieme; niente affondo su uno sci.",
  "基準：両板が同時に浮く。片板だけ沈み込まない。",
  "기준: 양 스키가 함께 떠오름; 한쪽만 잠기지 않음.",
  "Padrão: ambos os skis emergem juntos; sem afundar um só.")

p("Standard: glide on the outside ski; the inside ski taps the snow without taking weight.",
  "Critère : glissez sur le ski extérieur ; le ski intérieur tapote la neige sans prendre de poids.",
  "Standard: auf dem Außenski gleiten; Innenski tippt den Schnee ohne Last.",
  "Estándar: desliza sobre el esquí exterior; el interior toca la nieve sin cargar.",
  "Standard: scivola sullo sci esterno; lo sci interno sfiora la neve senza carico.",
  "基準：外側板で滑走。内側板は荷重せず雪を軽くタップ。",
  "기준: 바깥 스키로 활주; 안쪽은 하중 없이 설면을 톡톡.",
  "Padrão: deslize no ski exterior; o interior toca a neve sem carregar.")

p("Standard: hip over ankle in profile; knees unlocked.",
  "Critère : hanche au-dessus de la cheville de profil ; genoux déverrouillés.",
  "Standard: Hüfte über dem Knöchel im Profil; Knie nicht durchgedrückt.",
  "Estándar: cadera sobre el tobillo de perfil; rodillas desbloqueadas.",
  "Standard: anca sopra la caviglia di profilo; ginocchia sbloccate.",
  "基準：側面で股関節が足首の上。膝はロックしない。",
  "기준: 측면에서 고관절이 발목 위; 무릎 잠금 없음.",
  "Padrão: anca sobre o tornozelo de perfil; joelhos desbloqueados.")

p("Standard: hips incline into the turn, shoulders quiet, stance parallel.",
  "Critère : les hanches s’inclinent dans le virage, épaules calmes, skis parallèles.",
  "Standard: Hüften neigen in den Schwung, Schultern ruhig, Parallelstellung.",
  "Estándar: las caderas se inclinan a la curva, hombros quietos, postura paralela.",
  "Standard: le anche inclinano nella curva, spalle quiete, assetto parallelo.",
  "基準：股関節がターンへ傾き、肩は静か、スタンスはパラレル。",
  "기준: 고관절이 턴으로 기울고 어깨는 고요, 패러렐 스탠스.",
  "Padrão: as ancas inclinam na curva, ombros quietos, postura paralela.")

p("Standard: hips stay near the fall line; the knees still do the work.",
  "Critère : les hanches restent près de la ligne de pente ; les genoux font encore le travail.",
  "Standard: Hüften nahe der Falllinie; die Knie leisten die Arbeit.",
  "Estándar: las caderas se quedan cerca de la línea de máxima pendiente; las rodillas siguen trabajando.",
  "Standard: le anche restano vicino alla linea di massima pendenza; le ginocchia fanno ancora il lavoro.",
  "基準：股関節はフォールライン付近。仕事は膝がする。",
  "기준: 고관절은 폴라인 근처; 일은 무릎이 함.",
  "Padrão: as ancas ficam perto da linha de máxima pendente; os joelhos continuam a trabalhar.")

p("Standard: knees track over the toes; pelvis level.",
  "Critère : les genoux suivent les orteils ; bassin de niveau.",
  "Standard: Knie über den Zehen; Becken waagerecht.",
  "Estándar: las rodillas siguen los dedos; pelvis nivelada.",
  "Standard: le ginocchia seguono le punte; bacino livellato.",
  "基準：膝がつま先の上を通り、骨盤は水平。",
  "기준: 무릎이 발가락 위를 따르고 골반은 수평.",
  "Padrão: os joelhos acompanham os dedos; pélvis nivelada.")

p("Standard: left-right symmetry, even quieter shoulders.",
  "Critère : symétrie gauche-droite, épaules encore plus calmes.",
  "Standard: Links-Rechts-Symmetrie, noch ruhigere Schultern.",
  "Estándar: simetría izquierda-derecha, hombros aún más quietos.",
  "Standard: simmetria sinistra-destra, spalle ancora più quiete.",
  "基準：左右対称で、肩はさらに静か。",
  "기준: 좌우 대칭, 어깨는 더 고요.",
  "Padrão: simetria esquerda-direita, ombros ainda mais quietos.")

p("Standard: linked S-track, no dart to the edge; the wedge stays through the turn.",
  "Critère : trace en S enchaînée, pas de ruée vers le bord ; le chasse-neige reste dans le virage.",
  "Standard: verkettete S-Spur, kein Schuss zum Rand; der Pflug bleibt im Schwung.",
  "Estándar: huella en S enlazada, sin lanzarse al borde; la cuña se mantiene en la curva.",
  "Standard: traccia a S concatenata, senza scatto verso il bordo; lo spazzaneve resta in curva.",
  "基準：連続S軌跡で端へ突っ込まない。ターン中プルークは残る。",
  "기준: 연결 S 자국, 가장자리로 돌진하지 않음; 턴 중 플루크 유지.",
  "Padrão: rasto em S encadeado, sem disparo para a margem; a cunha mantém-se na curva.")

p("Standard: no long traverse between turns; knees flex and extend.",
  "Critère : pas de longue traversée entre les virages ; genoux qui fléchissent et s’étendent.",
  "Standard: keine lange Querfahrt zwischen Schwüngen; Knie beugen und strecken.",
  "Estándar: sin travesía larga entre curvas; las rodillas flexionan y extienden.",
  "Standard: niente lunga diagonale tra le curve; ginocchia che flettono ed estendono.",
  "基準：ターン間の長いトラバースなし。膝の屈伸あり。",
  "기준: 턴 사이 긴 트래버스 없음; 무릎 굴신.",
  "Padrão: sem travessia longa entre curvas; joelhos fletem e estendem.")

p("Standard: on replay, the wrists stay below the shoulders.",
  "Critère : au ralenti, les poignets restent sous les épaules.",
  "Standard: in der Wiederholung bleiben die Handgelenke unter den Schultern.",
  "Estándar: en la repetición, las muñecas quedan por debajo de los hombros.",
  "Standard: in replay, i polsi restano sotto le spalle.",
  "基準：リプレイで手首が肩より下。",
  "기준: 리플레이에서 손목이 어깨 아래.",
  "Padrão: no replay, os pulsos ficam abaixo dos ombros.")

p("Standard: quiet torso, large knee travel, no straight-leg slam.",
  "Critère : torse calme, grand débattement de genou, pas d’impact jambe tendue.",
  "Standard: ruhiger Rumpf, großer Kniehub, kein Schlag mit gestrecktem Bein.",
  "Estándar: torso quieto, gran recorrido de rodilla, sin impacto de pierna recta.",
  "Standard: busto quieto, grande escursione del ginocchio, niente impatto a gamba tesa.",
  "基準：胴は静か、膝の振幅は大きく、伸ばし脚の叩きつけなし。",
  "기준: 몸통 고요, 무릎 가동 큼, 펴진 다리 착지 충격 없음.",
  "Padrão: tronco quieto, grande curso do joelho, sem impacto de perna esticada.")

p("Standard: stance narrows in the last third of the turn, still stable.",
  "Critère : l’écartement se resserre au dernier tiers du virage, toujours stable.",
  "Standard: Standbreite verengt sich im letzten Drittel des Schwungs, bleibt stabil.",
  "Estándar: la base se estrecha en el último tercio de la curva, aún estable.",
  "Standard: la base si restringe nell’ultimo terzo della curva, ancora stabile.",
  "基準：ターン後半1/3でスタンスが狭まり、なお安定。",
  "기준: 턴 마지막 1/3에서 스탠스가 좁아지되 안정 유지.",
  "Padrão: a base estreita no último terço da curva, ainda estável.")

p("Standard: stop on a mark both ways; skis parallel, not in a wedge.",
  "Critère : arrêt sur une marque dans les deux sens ; skis parallèles, pas en chasse-neige.",
  "Standard: Stopp auf Markierung beide Richtungen; parallel, nicht im Pflug.",
  "Estándar: parada en una marca en ambos sentidos; esquís paralelos, no en cuña.",
  "Standard: stop su un segno in entrambe le direzioni; sci paralleli, non a spazzaneve.",
  "基準：両方向で目印に停止。板はパラレルでプルークではない。",
  "기준: 양방향으로 표지에 정지; 패러렐이지 플루크 아님.",
  "Padrão: paragem numa marca nos dois sentidos; skis paralelos, não em cunha.")

p("Standard: ten stops, tips close, torso facing downhill.",
  "Critère : dix arrêts, spatules rapprochées, torse face à la vallée.",
  "Standard: zehn Stopps, Spitzen nah, Rumpf talwärts.",
  "Estándar: diez paradas, puntas juntas, tronco mirando valle abajo.",
  "Standard: dieci stop, punte vicine, busto rivolto a valle.",
  "基準：10回停止、チップ接近、胴は谷向き。",
  "기준: 정지 10회, 팁 가깝게, 몸통 계곡 방향.",
  "Padrão: dez paragens, pontas próximas, tronco virado para o vale.")

p("Standard: the same count on every turn, with the deepest flexion in the middle of the arc.",
  "Critère : le même décompte à chaque virage, flexion la plus profonde au milieu de l’arc.",
  "Standard: derselbe Count in jedem Schwung, tiefste Beugung in der Bogenmitte.",
  "Estándar: el mismo conteo en cada curva, con la flexión más profunda en el medio del arco.",
  "Standard: lo stesso conteggio a ogni curva, flessione più profonda a metà arco.",
  "基準：毎ターン同じカウント。最深屈曲は弧の中ほど。",
  "기준: 매 턴 같은 카운트, 가장 깊은 굴곡은 아크 중간.",
  "Padrão: a mesma contagem em cada curva, com a flexão mais profunda a meio do arco.")

p("Standard: the shoulders keep facing down the pitch through every pivot.",
  "Critère : les épaules restent face à la pente à chaque pivot.",
  "Standard: Schultern bleiben bei jedem Pivot talwärts zur Piste.",
  "Estándar: los hombros siguen mirando valle abajo en cada pivote.",
  "Standard: le spalle restano rivolte a valle a ogni pivot.",
  "基準：毎ピボットで肩は斜面下向きのまま。",
  "기준: 매 피벗에서 어깨가 슬로프 아래를 향함.",
  "Padrão: os ombros mantêm-se virados para baixo da pendente em cada pivot.")

p("Standard: the skis start to turn while the shoulders still face downhill.",
  "Critère : les skis commencent à tourner alors que les épaules restent face à la vallée.",
  "Standard: die Ski beginnen zu drehen, während die Schultern noch talwärts zeigen.",
  "Estándar: los esquís empiezan a girar mientras los hombros siguen mirando valle abajo.",
  "Standard: gli sci iniziano a virare mentre le spalle restano rivolte a valle.",
  "基準：肩がまだ谷を向いたまま板が回り始める。",
  "기준: 어깨가 아직 계곡을 향한 채 스키가 돌기 시작.",
  "Padrão: os skis começam a virar enquanto os ombros ainda enfrentam o vale.")

p("Standard: the skis stay across the hill and the torso does not turn with them.",
  "Critère : les skis restent en travers de la pente et le torse ne tourne pas avec eux.",
  "Standard: die Ski bleiben quer zum Hang und der Rumpf dreht nicht mit.",
  "Estándar: los esquís se mantienen transversales a la pendiente y el tronco no gira con ellos.",
  "Standard: gli sci restano di traverso al pendio e il busto non gira con loro.",
  "基準：板は斜面横断のまま、胴は一緒に回らない。",
  "기준: 스키는 사면을 가로지른 채, 몸통은 함께 돌지 않음.",
  "Padrão: os skis ficam transversais à pendente e o tronco não roda com eles.")

out = Path("locales/_ski_locale_fills/part05.json")
out.write_text(json.dumps(T, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("wrote", len(T), "->", out)
