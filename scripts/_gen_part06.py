# -*- coding: utf-8 -*-
import json
from pathlib import Path

def L(fr, de, es, it, ja, ko, pt):
    return dict(fr=fr, de=de, es=es, it=it, ja=ja, ko=ko, pt=pt)

T = {}

def p(en, fr, de, es, it, ja, ko, pt):
    T[en] = L(fr, de, es, it, ja, ko, pt)

# --- coaching + UI batch (professional ski register) ---
p("Start analysis",
  "Lancer l’analyse", "Analyse starten", "Iniciar análisis", "Avvia analisi",
  "分析を開始", "분석 시작", "Iniciar análise")
p("Static",
  "Fixe", "Statisch", "Fija", "Fissa",
  "固定", "고정", "Fixa")
p("Static camera",
  "Caméra fixe", "Statische Kamera", "Cámara fija", "Camera fissa",
  "固定カメラ", "고정 카메라", "Câmara fixa")
p("Stay centered so you can move onto the new outside ski.",
  "Restez centré pour pouvoir passer sur le nouveau ski extérieur.",
  "Mittig bleiben, damit du auf den neuen Außenski wechseln kannst.",
  "Mantente centrado para poder pasar al nuevo esquí exterior.",
  "Resta centrato così puoi passare sul nuovo sci esterno.",
  "ニュートラルに立ち、新しい外側スキーへ移れるように。",
  "중심을 잡아 새 바깥쪽 스키로 옮길 수 있게 하세요.",
  "Mantenha-se centrado para poder passar para o novo ski exterior.")
p("Stay in a wedge through the turn; load the outside ski.",
  "Gardez le chasse-neige pendant le virage ; chargez le ski extérieur.",
  "Im Pflug durch den Schwung bleiben; den Außenski belasten.",
  "Mantén la cuña durante la curva; carga el esquí exterior.",
  "Mantieni lo spazzaneve nella curva; carica lo sci esterno.",
  "ターン中はプルークのまま。外側スキーに荷重。",
  "턴 내내 플루크를 유지하고 바깥쪽 스키에 하중을 주세요.",
  "Mantenha a cunha durante a curva; carregue o ski exterior.")
p("Stay near the fall line",
  "Restez près de la ligne de pente",
  "Nah an der Falllinie bleiben",
  "Quédate cerca de la línea de máxima pendiente",
  "Resta vicino alla linea di massima pendenza",
  "フォールライン近くを保つ",
  "폴라인 근처를 유지",
  "Fique perto da linha de máxima pendente")
p("Stay parallel or inclination becomes banking.",
  "Restez parallèle, sinon l’inclinaison devient un banking.",
  "Parallel bleiben, sonst wird die Neigung zum Banking.",
  "Mantén el paralelo o la inclinación se vuelve banking.",
  "Resta parallelo, altrimenti l’inclinazione diventa banking.",
  "パラレルを保て。でないと傾きがバンキングになる。",
  "패러렐을 유지하세요. 아니면 기울기가 뱅킹이 됩니다.",
  "Mantenha o paralelo ou a inclinação vira banking.")
p("Steep/hard suggestion for fall-line moguls only; still not measured.",
  "Suggestion raide/dure uniquement pour bosses en ligne de pente ; toujours non mesuré.",
  "Steil/hart-Vorschlag nur für Falllinien-Buckel; weiterhin nicht gemessen.",
  "Sugerencia empinada/dura solo para baches en máxima pendiente; aún no se mide.",
  "Suggerimento ripido/duro solo per gobbe in linea di massima pendenza; ancora non misurato.",
  "フォールライン・モーグル向けの急/硬提案のみ。計測はしない。",
  "폴라인 모글 전용 급경사/하드 제안. 여전히 미측정.",
  "Sugestão íngreme/dura só para moguls na linha de máxima pendente; ainda não medido.")
p("Steeper groomed red run; for medium and short carve heuristics.",
  "Piste rouge damée plus raide ; pour heuristiques carving moyen et court.",
  "Steilere präparierte rote Piste; für Mittel- und Kurz-Carving-Heuristiken.",
  "Pista roja pisada más empinada; para heurísticas de carving medio y corto.",
  "Pista rossa battuta più ripida; per euristiche di carving medio e corto.",
  "やや急な整備赤斜面。ミドル／ショート・カービングの経験則向け。",
  "더 가파른 정비 레드; 미들·숏 카빙 휴리스틱용.",
  "Pista vermelha preparada mais íngreme; para heurísticas de carving médio e curto.")
p("Steeps",
  "Pentes raides", "Steilhänge", "Pendientes fuertes", "Pendii ripidi",
  "急斜面", "급경사", "Pendentes íngremes")
p("Stem",
  "Stem", "Stemm", "Stem", "Stem",
  "ステム", "스템", "Stem")
p("Stemmed transitions",
  "Transitions en stem", "Gestemmte Übergänge", "Transiciones en stem", "Transizioni in stem",
  "ステム遷移", "스템 전환", "Transições em stem")
p("Stop",
  "Stop", "Stopp", "Parar", "Stop",
  "停止", "정지", "Parar")
p("Straight-run a soft slope and bounce six times, then link the bounces into turns.",
  "Descendez droit une pente douce et rebondissez six fois, puis enchaînez les rebonds en virages.",
  "Weiche Piste geradeaus und sechsmal federn, dann die Federn zu Schwüngen verbinden.",
  "Baja en línea por pendiente suave y rebota seis veces; luego encadena los rebotes en curvas.",
  "Scendi dritto su pendio morbido e rimbalza sei volte, poi collega i rimbalzi in curve.",
  "柔らかい斜面を直滑降し六回バウンス、その後バウンスをターンに繋ぐ。",
  "부드러운 슬로프를 직활하며 여섯 번 바운스한 뒤, 바운스를 턴으로 연결하세요.",
  "Desça em linha numa pendente macia e salte seis vezes; depois encadeie os saltos em curvas.")
p("Strong",
  "Fort", "Stark", "Fuerte", "Forte",
  "強い", "강함", "Forte")
p("Suggested black run; slope is not measured.",
  "Piste noire suggérée ; la pente n’est pas mesurée.",
  "Vorgeschlagene schwarze Piste; Neigung nicht gemessen.",
  "Pista negra sugerida; la pendiente no se mide.",
  "Pista nera suggerita; la pendenza non è misurata.",
  "黒斜面の提案。斜度は未測定。",
  "블랙 슬로프 제안. 경사도는 미측정.",
  "Pista preta sugerida; a pendente não é medida.")
p("Suggested blue run; slope is not measured.",
  "Piste bleue suggérée ; la pente n’est pas mesurée.",
  "Vorgeschlagene blaue Piste; Neigung nicht gemessen.",
  "Pista azul sugerida; la pendiente no se mide.",
  "Pista blu suggerita; la pendenza non è misurata.",
  "青斜面の提案。斜度は未測定。",
  "블루 슬로프 제안. 경사도는 미측정.",
  "Pista azul sugerida; a pendente não é medida.")
p("Suggested green run; slope is not measured.",
  "Piste verte suggérée ; la pente n’est pas mesurée.",
  "Vorgeschlagene grüne Piste; Neigung nicht gemessen.",
  "Pista verde sugerida; la pendiente no se mide.",
  "Pista verde suggerita; la pendenza non è misurata.",
  "緑斜面の提案。斜度は未測定。",
  "그린 슬로프 제안. 경사도는 미측정.",
  "Pista verde sugerida; a pendente não é medida.")
p("Suggested mogul field; bump shape is not measured.",
  "Champ de bosses suggéré ; la forme des bosses n’est pas mesurée.",
  "Vorgeschlagenes Buckelfeld; Buckelform nicht gemessen.",
  "Campo de baches sugerido; la forma del bache no se mide.",
  "Campo di gobbe suggerito; la forma delle gobbe non è misurata.",
  "モーグル畑の提案。バンプ形状は未測定。",
  "모글 필드 제안. 범프 형태는 미측정.",
  "Campo de moguls sugerido; a forma dos bumps não é medida.")
p("Suggested off-piste inside the resort boundary; snow depth is not measured.",
  "Hors-piste suggéré dans les limites de la station ; l’épaisseur de neige n’est pas mesurée.",
  "Vorgeschlagene Offpiste innerhalb der Gebietsgrenze; Schneetiefe nicht gemessen.",
  "Fuera de pista sugerido dentro del dominio; la profundidad de nieve no se mide.",
  "Fuori pista suggerito dentro il comprensorio; lo spessore neve non è misurato.",
  "ゲレンデ境界内オフピステの提案。雪深は未測定。",
  "리조트 경계 내 오프피스테 제안. 설심은 미측정.",
  "Fora de pista sugerido dentro do domínio; a profundidade da neve não é medida.")
p("Suggested park terrain; this app does not score air.",
  "Terrain de park suggéré ; cette appli ne note pas l’air.",
  "Vorgeschlagenes Park-Gelände; diese App wertet Air nicht.",
  "Terreno de park sugerido; esta app no puntúa el air.",
  "Terreno park suggerito; questa app non valuta l’air.",
  "パーク地形の提案。このアプリはエアを採点しない。",
  "파크 지형 제안. 이 앱은 에어를 채점하지 않습니다.",
  "Terreno de park sugerido; esta app não pontua air.")
p("Suggested red run; slope is not measured.",
  "Piste rouge suggérée ; la pente n’est pas mesurée.",
  "Vorgeschlagene rote Piste; Neigung nicht gemessen.",
  "Pista roja sugerida; la pendiente no se mide.",
  "Pista rossa suggerita; la pendenza non è misurata.",
  "赤斜面の提案。斜度は未測定。",
  "레드 슬로프 제안. 경사도는 미측정.",
  "Pista vermelha sugerida; a pendente não é medida.")
p("Suggested trail rating",
  "Niveau de piste suggéré", "Vorgeschlagene Pistenbewertung", "Nivel de pista sugerido", "Livello pista suggerito",
  "提案ゲレンデ難易度", "제안 슬로프 등급", "Classificação de pista sugerida")
p("Suggested: {snow} / {terrain}",
  "Suggestion : {snow} / {terrain}", "Vorschlag: {snow} / {terrain}", "Sugerido: {snow} / {terrain}", "Suggerito: {snow} / {terrain}",
  "提案：{snow} / {terrain}", "제안: {snow} / {terrain}", "Sugerido: {snow} / {terrain}")
p("Summary",
  "Résumé", "Zusammenfassung", "Resumen", "Riepilogo",
  "要約", "요약", "Resumo")
p("Switch alpine",
  "Alpine switch", "Switch Alpin", "Switch alpino", "Switch alpino",
  "スイッチアルペン", "스위치 알파인", "Switch alpine")
p("Symptom",
  "Symptôme", "Symptom", "Síntoma", "Sintomo",
  "症状", "증상", "Sintoma")
p("Tactic",
  "Tactique", "Taktik", "Táctica", "Tattica",
  "タクティック", "전술", "Tática")
p("Tech: skeleton criteria (from knowledge base)",
  "Tech : critères squelette (base de connaissances)",
  "Tech: Skelett-Kriterien (Wissensbasis)",
  "Tech: criterios de esqueleto (base de conocimiento)",
  "Tech: criteri scheletro (base di conoscenza)",
  "Tech：骨格判定基準（知識ベース）",
  "Tech: 스켈레톤 기준（지식 베이스）",
  "Tech: critérios de esqueleto (base de conhecimento)")
p("Ten linked parallel turns on a blue run, counting one-two through every turn.",
  "Dix virages parallèles enchaînés sur piste bleue, en comptant un-deux à chaque virage.",
  "Zehn verkettete Parallelschwünge auf blauer Piste, bei jedem Schwung eins-zwei zählen.",
  "Diez curvas paralelas enlazadas en pista azul, contando uno-dos en cada curva.",
  "Dieci curve parallele concatenate su pista blu, contando uno-due in ogni curva.",
  "青斜面で連続パラレル10本。各ターンでワン・ツーと数える。",
  "블루에서 연결 패러렐 10회. 매 턴마다 원-투로 세기.",
  "Dez curvas paralelas encadeadas numa pista azul, contando um-dois em cada curva.")
p("Ten short turns on a blue run; quiet shoulders, hands low.",
  "Dix virages courts sur piste bleue ; épaules calmes, mains basses.",
  "Zehn Kurzschwünge auf blauer Piste; ruhige Schultern, tiefe Hände.",
  "Diez curvas cortas en pista azul; hombros quietos, manos bajas.",
  "Dieci curve corte su pista blu; spalle quiete, mani basse.",
  "青斜面でショートターン10本。肩は静か、手は低く。",
  "블루에서 숏턴 10회. 어깨는 조용히, 손은 낮게.",
  "Dez curvas curtas numa pista azul; ombros quietos, mãos baixas.")
p("Terrain",
  "Terrain", "Gelände", "Terreno", "Terreno",
  "地形", "지형", "Terreno")
p("Terrain and venue",
  "Terrain et lieu", "Gelände und Ort", "Terreno y lugar", "Terreno e sede",
  "地形と会場", "지형과 장소", "Terreno e local")
p("Terrain needed",
  "Terrain requis", "Gelände erforderlich", "Terreno necesario", "Terreno richiesto",
  "地形が必要", "지형 필요", "Terreno necessário")
p("Terrain, slope and snow are optional \u2014 set Terrain to Mogul run for mogul detection.",
  "Terrain, pente et neige sont optionnels \u2014 réglez Terrain sur Piste de bosses pour détecter les bosses.",
  "Gelände, Neigung und Schnee sind optional \u2014 setze Gelände auf Buckelpiste für Buckelerkennung.",
  "Terreno, pendiente y nieve son opcionales \u2014 pon Terreno en Pista de baches para detectar moguls.",
  "Terreno, pendenza e neve sono opzionali \u2014 imposta Terreno su Pista gobbe per rilevare le gobbe.",
  "地形・斜度・雪質は任意——モーグル検出には地形を「モーグルラン」に。",
  "지형·경사·설질은 선택——모글 감지 시 지형을 「모글 런」으로 설정.",
  "Terreno, pendente e neve são opcionais \u2014 defina Terreno como Pista de moguls para detetar moguls.")
p("Terrain park",
  "Snowpark", "Terrainpark", "Snowpark", "Snowpark",
  "テレインパーク", "지형 파크", "Snowpark")
p("Groomed piste",
  "Piste damée", "Präparierte Piste", "Pista pisada", "Pista battuta",
  "圧雪ゲレンデ", "정비 슬로프", "Pista preparada")
p("Mogul run",
  "Piste de bosses", "Buckelpiste", "Pista de baches", "Pista gobbe",
  "モーグルラン", "모글 런", "Pista de moguls")
p("Test it",
  "Testez-le", "Ausprobieren", "Pruébalo", "Provalo",
  "試す", "테스트하기", "Testar")
p("The allowance is {n}",
  "La tolérance est de {n}", "Die Zulassung beträgt {n}", "El margen es {n}", "Il margine è {n}",
  "許容は {n}", "허용치는 {n}", "A margem é {n}")
p("The camera follows the skier, so turn rhythm is measured from the body rather than the track.",
  "La caméra suit le skieur : le rythme de virage se mesure sur le corps, pas sur la trace.",
  "Die Kamera folgt dem Fahrer; der Schwungrhythmus wird am Körper gemessen, nicht an der Spur.",
  "La cámara sigue al esquiador: el ritmo de curva se mide en el cuerpo, no en la huella.",
  "La camera segue lo sciatore: il ritmo di curva si misura sul corpo, non sulla traccia.",
  "カメラが滑走者を追うため、ターンリズムは軌跡ではなく体から測る。",
  "카메라가 스키어를 따라가므로 턴 리듬은 궤적이 아니라 몸에서 측정합니다.",
  "A câmara segue o esquiador: o ritmo de curva mede-se no corpo, não no rasto.")
p("The camera pans during the clip; a fixed camera measures rhythm more reliably.",
  "La caméra fait un panoramique dans le clip ; une caméra fixe mesure le rythme plus fiablement.",
  "Die Kamera schwenkt im Clip; eine feste Kamera misst den Rhythmus zuverlässiger.",
  "La cámara panea en el clip; una cámara fija mide el ritmo con más fiabilidad.",
  "La camera fa panoramica nel clip; una camera fissa misura il ritmo in modo più affidabile.",
  "クリップ中にカメラがパンしている。固定カメラの方がリズム計測が安定する。",
  "클립 중 카메라가 패닝합니다. 고정 카메라가 리듬을 더 안정적으로 측정합니다.",
  "A câmara faz pan no clip; uma câmara fixa mede o ritmo com mais fiabilidade.")
p("The clip is too short to judge rhythm. Film a whole run of at least eight turns.",
  "Le clip est trop court pour juger le rythme. Filmez une descente d’au moins huit virages.",
  "Der Clip ist zu kurz für den Rhythmus. Filme eine ganze Abfahrt mit mindestens acht Schwüngen.",
  "El clip es demasiado corto para juzgar el ritmo. Graba una bajada de al menos ocho curvas.",
  "Il clip è troppo corto per giudicare il ritmo. Filma una discesa di almeno otto curve.",
  "クリップが短くリズムを判定できない。少なくとも8ターンの一連を撮影して。",
  "클립이 너무 짧아 리듬을 판단할 수 없습니다. 최소 여덟 턴의 한 런을 촬영하세요.",
  "O clip é demasiado curto para julgar o ritmo. Filme uma descida com pelo menos oito curvas.")
p("The question to answer",
  "La question à trancher", "Die zu beantwortende Frage", "La pregunta a responder", "La domanda da rispondere",
  "答えるべき問い", "답할 질문", "A pergunta a responder")
p("The shoulders keep facing down the pitch while the legs turn underneath.",
  "Les épaules restent face à la pente tandis que les jambes tournent en dessous.",
  "Die Schultern bleiben talwärts, während die Beine darunter drehen.",
  "Los hombros siguen mirando valle abajo mientras las piernas giran debajo.",
  "Le spalle restano verso valle mentre le gambe girano sotto.",
  "肩は斜面下向きのまま、脚がその下で回る。",
  "어깨는 밸리 방향을 유지하고 그 아래에서 다리가 돕니다.",
  "Os ombros mantêm-se virados para baixo da pendente enquanto as pernas giram por baixo.")
p("The shoulders stay square to the fall line while the skis slip.",
  "Les épaules restent d’équerre à la ligne de pente pendant que les skis dérapent.",
  "Die Schultern bleiben quer zur Falllinie, während die Ski driften.",
  "Los hombros quedan al cuadrado con la línea de máxima pendiente mientras los esquís derrapan.",
  "Le spalle restano perpendicolari alla linea di massima pendenza mentre gli sci derapano.",
  "スキーがスキッドする間、肩はフォールラインに正対したまま。",
  "스키가 스키드하는 동안 어깨는 폴라인에 정면을 유지합니다.",
  "Os ombros ficam ao esquadro com a linha de máxima pendente enquanto os skis derrapam.")
p("The skeleton is weak in this clip: get closer, keep the skier unoccluded, and avoid flat light.",
  "Le squelette est faible dans ce clip : rapprochez-vous, gardez le skieur dégagé et évitez la lumière plate.",
  "Das Skelett ist schwach in diesem Clip: näher rangehen, Fahrer frei halten, Flachlicht meiden.",
  "El esqueleto es débil en este clip: acércate, mantén al esquiador sin oclusión y evita luz plana.",
  "Lo scheletro è debole in questo clip: avvicinati, tieni lo sciatore libero e evita luce piatta.",
  "このクリップの骨格が弱い：寄る、遮られない、フラット光を避ける。",
  "이 클립의 스켈레톤이 약합니다: 더 가까이, 스키어가 가려지지 않게, 플랫 라이트를 피하세요.",
  "O esqueleto está fraco neste clip: aproxime-se, mantenha o esquiador sem oclusão e evite luz plana.")
p("The skeleton was too small or incomplete to measure.",
  "Le squelette était trop petit ou incomplet pour mesurer.",
  "Das Skelett war zu klein oder unvollständig zum Messen.",
  "El esqueleto era demasiado pequeño o incompleto para medir.",
  "Lo scheletro era troppo piccolo o incompleto per misurare.",
  "骨格が小さすぎるか不完全で測定できない。",
  "스켈레톤이 너무 작거나 불완전해 측정할 수 없습니다.",
  "O esqueleto era demasiado pequeno ou incompleto para medir.")
p("The {joints} could not be tracked in this clip.",
  "Les {joints} n’ont pas pu être suivis dans ce clip.",
  "Die {joints} konnten in diesem Clip nicht getrackt werden.",
  "No se pudieron rastrear los {joints} en este clip.",
  "I {joints} non sono stati tracciabili in questo clip.",
  "このクリップでは{joints}を追跡できませんでした。",
  "이 클립에서 {joints}을(를) 추적할 수 없습니다.",
  "Não foi possível seguir os {joints} neste clip.")
p("This clip is still processing. Play it when it is done.",
  "Ce clip est encore en cours de traitement. Lisez-le une fois terminé.",
  "Dieser Clip wird noch verarbeitet. Abspielen, wenn fertig.",
  "Este clip aún se está procesando. Reprodúcelo cuando termine.",
  "Questo clip è ancora in elaborazione. Riproducilo a fine lavoro.",
  "このクリップは処理中です。完了してから再生してください。",
  "이 클립은 아직 처리 중입니다. 끝나면 재생하세요.",
  "Este clip ainda está a processar. Reproduza quando terminar.")
p("Three-quarter view",
  "Vue de trois quarts", "Dreiviertelansicht", "Vista de tres cuartos", "Vista a tre quarti",
  "斜め前ビュー", "사분삼 뷰", "Vista de três quartos")
p("Throwing the shoulders wrecks inclination.",
  "Jeter les épaules ruine l’inclinaison.",
  "Schultern werfen zerstört die Neigung.",
  "Lanzar los hombros destroza la inclinación.",
  "Gettare le spalle rovina l’inclinazione.",
  "肩を放り出すとインクラインが崩れる。",
  "어깨를 던지면 인클리네이션이 무너집니다.",
  "Lançar os ombros destrói a inclinação.")
p("TikTok",
  "TikTok", "TikTok", "TikTok", "TikTok",
  "TikTok", "TikTok", "TikTok")
p("Tip the body into the turn (hips inside the arc). Heuristic only \u2014 not a measured edge angle or FIS score.",
  "Inclinez le corps dans le virage (hanches à l’intérieur de l’arc). Heuristique seulement \u2014 pas un angle de carre mesuré ni un score FIS.",
  "Körper in den Schwung neigen (Hüfte innen im Bogen). Nur Heuristik \u2014 kein gemessener Kantenwinkel oder FIS-Score.",
  "Inclina el cuerpo hacia la curva (caderas dentro del arco). Solo heurística \u2014 no es ángulo de canto medido ni puntuación FIS.",
  "Inclina il corpo nella curva (anche dentro l’arco). Solo euristica \u2014 non angolo di lama misurato né punteggio FIS.",
  "体をターン内側へ傾ける（ヒップは弧の内側）。経験則のみ——実測エッジ角やFIS得点ではない。",
  "몸을 턴 안으로 기울이세요(엉덩이는 아크 안쪽). 휴리스틱일 뿐——실측 엣지 각이나 FIS 점수가 아님.",
  "Incline o corpo para a curva (ancas dentro do arco). Só heurística \u2014 não é ângulo de canto medido nem pontuação FIS.")
p("Tips close, tails open, stance wider than the hips.",
  "Pointes rapprochées, talons ouverts, écartement plus large que les hanches.",
  "Spitzen nah, Enden offen, Standbreite weiter als die Hüfte.",
  "Puntas juntas, colas abiertas, base más ancha que las caderas.",
  "Punte vicine, code aperte, base più larga del bacino.",
  "チップは寄せ、テールは開き、スタンスは腰より広く。",
  "팁은 모으고 테일은 벌리며, 스탠스는 엉덩이보다 넓게.",
  "Pontas juntas, caudas abertas, base mais larga que as ancas.")
p("Torso downhill",
  "Torse vers l’aval", "Rumpf talwärts", "Torso valle abajo", "Torso a valle",
  "体幹は山下へ", "몸통 밸리 방향", "Tronco a vale")
p("Torso faces downhill",
  "Le torse fait face à l’aval", "Rumpf schaut talwärts", "El torso mira valle abajo", "Il torso guarda a valle",
  "体幹は山下向き", "몸통이 밸리를 향함", "O tronco olha a vale")
p("Train {name}.",
  "Travaillez {name}.", "Trainiere {name}.", "Entrena {name}.", "Allena {name}.",
  "{name}を練習。", "{name}을(를) 훈련하세요.", "Treine {name}.")
p("Train {name}: the standard is {standard}.",
  "Travaillez {name} : le standard est {standard}.",
  "Trainiere {name}: der Standard ist {standard}.",
  "Entrena {name}: el estándar es {standard}.",
  "Allena {name}: lo standard è {standard}.",
  "{name}を練習：基準は{standard}。",
  "{name} 훈련: 기준은 {standard}.",
  "Treine {name}: o padrão é {standard}.")
p("Training emphasis",
  "Accent d’entraînement", "Trainingsschwerpunkt", "Énfasis de entrenamiento", "Enfasi di allenamento",
  "トレーニング重点", "훈련 중점", "Ênfase de treino")
p("Training venue",
  "Lieu d’entraînement", "Trainingsort", "Lugar de entrenamiento", "Sede di allenamento",
  "練習場所", "훈련 장소", "Local de treino")
p("Trim video (max 2 minutes)",
  "Rogner la vidéo (max 2 minutes)", "Video zuschneiden (max. 2 Minuten)", "Recortar vídeo (máx. 2 minutos)", "Taglia video (max 2 minuti)",
  "動画をトリム（最大2分）", "영상 자르기(최대 2분)", "Recortar vídeo (máx. 2 minutos)")
p("Trough fall-line rhythm",
  "Rythme en creux de ligne de pente", "Rhythmus in der Falllinien-Rinne", "Ritmo en el canal de máxima pendiente", "Ritmo nel canale di massima pendenza",
  "トラフ・フォールライン・リズム", "골 폴라인 리듬", "Ritmo no canal da linha de máxima pendente")
p("Turn amplitude",
  "Amplitude de virage", "Schwungamplitude", "Amplitud de curva", "Ampiezza di curva",
  "ターン振幅", "턴 진폭", "Amplitude de curva")
p("Turn durations stay close to each other; no long traverse between turns.",
  "Les durées de virage restent proches ; pas de longue traversée entre les virages.",
  "Schwungdauern bleiben nah beieinander; keine lange Schrägfahrt dazwischen.",
  "Las duraciones de curva se mantienen cercanas; sin travesía larga entre curvas.",
  "Le durate di curva restano vicine; niente lunga diagonale tra le curve.",
  "各ターン時間は揃える。ターン間の長い斜滑降はなし。",
  "턴 지속 시간이 비슷해야 합니다. 턴 사이 긴 트래버스는 없습니다.",
  "As durações das curvas ficam próximas; sem travessia longa entre curvas.")
p("Turn faults",
  "Défauts de virage", "Schwungfehler", "Fallos de curva", "Difetti di curva",
  "ターンの欠点", "턴 결함", "Falhas de curva")
p("Turn instead of side-slipping the pitch",
  "Tournez plutôt que de déraper latéralement la pente",
  "Schwingen statt die Piste seitwärts zu rutschen",
  "Gira en vez de derrapar de lado la pendiente",
  "Curva invece di derapare di lato il pendio",
  "斜面を横滑りせずターンする",
  "슬로프를 옆미끄럼 하지 말고 턴하세요",
  "Curve em vez de derrapar de lado a pendente")
p("Turn rate",
  "Cadence de virage", "Schwungrate", "Cadencia de curva", "Frequenza di curva",
  "ターンレート", "턴 레이트", "Cadência de curva")
p("Turn shape",
  "Forme de virage", "Schwungform", "Forma de curva", "Forma di curva",
  "ターン形状", "턴 모양", "Forma de curva")
p("Turn-by-turn",
  "Virage par virage", "Schwung für Schwung", "Curva a curva", "Curva per curva",
  "ターン別", "턴별", "Curva a curva")
p("Turns detected",
  "Virages détectés", "Erkannte Schwünge", "Curvas detectadas", "Curve rilevate",
  "検出されたターン", "감지된 턴", "Curvas detetadas")
p("Turns led by the shoulders",
  "Virages menés par les épaules", "Von den Schultern geführte Schwünge", "Curvas lideradas por los hombros", "Curve guidate dalle spalle",
  "肩主導のターン", "어깨가 이끄는 턴", "Curvas puxadas pelos ombros")
p("Two-footed powder bounce",
  "Rebond poudreuse à deux pieds", "Beidbeiniger Powder-Bounce", "Rebote de polvo a dos pies", "Rimbalzo powder a due piedi",
  "両足パウダーバウンス", "양발 파우더 바운스", "Salto em powder a dois pés")
p("Two-footed, rounder turns in soft snow; flex and extend to make the skis surface.",
  "Virages plus ronds à deux pieds en neige souple ; fléchissez et étendez pour faire remonter les skis.",
  "Beidbeinige, rundere Schwünge im Weichschnee; beugen und strecken, damit die Ski aufschwimmen.",
  "Curvas más redondas a dos pies en nieve blanda; flexiona y extiende para hacer flotar los esquís.",
  "Curve più rotonde a due piedi su neve morbida; fletti ed estendi per far affiorare gli sci.",
  "軟雪では両足の丸いターン。蹲伸でスキーを浮かせる。",
  "부드러운 눈에서 양발의 더 둥근 턴; 굴신으로 스키를 띄우세요.",
  "Curvas mais redondas a dois pés na neve macia; flexione e estenda para fazer os skis emergir.")
p("Unknown",
  "Inconnu", "Unbekannt", "Desconocido", "Sconosciuto",
  "不明", "알 수 없음", "Desconhecido")
p("Undo label point",
  "Annuler le point d’étiquette", "Labelpunkt rückgängig", "Deshacer punto de etiqueta", "Annulla punto etichetta",
  "ラベル点を取り消す", "라벨 점 실행 취소", "Anular ponto de etiqueta")
p("Unlike",
  "Unlike", "Unlike", "Unlike", "Unlike",
  "Unlike", "Unlike", "Unlike")
p("Unscored when the head is not visible in 2D pose.",
  "Non noté si la tête n’est pas visible en pose 2D.",
  "Unbewertet, wenn der Kopf in der 2D-Pose nicht sichtbar ist.",
  "Sin puntuar si la cabeza no es visible en pose 2D.",
  "Non valutato se la testa non è visibile in posa 2D.",
  "2Dポーズで頭が見えない場合は採点しない。",
  "2D 포즈에서 머리가 보이지 않으면 채점하지 않습니다.",
  "Não pontuado se a cabeça não for visível na pose 2D.")
p("Unspecified",
  "Non précisé", "Unbestimmt", "No especificado", "Non specificato",
  "未指定", "미지정", "Não especificado")
p("Unstable camera, occlusion, or out-of-scope terrain: no stage claim.",
  "Caméra instable, occlusion ou terrain hors portée : pas de niveau affirmé.",
  "Instabile Kamera, Occlusion oder Gelände außerhalb: kein Stufenanspruch.",
  "Cámara inestable, oclusión o terreno fuera de alcance: sin afirmación de nivel.",
  "Camera instabile, occlusione o terreno fuori portata: nessun livello dichiarato.",
  "カメラ不安定・遮蔽・対象外地形：段階判定なし。",
  "불안정한 카메라, 가림, 범위 밖 지형: 단계 판정 없음.",
  "Câmara instável, oclusão ou terreno fora de alcance: sem afirmação de nível.")
p("Unsupported file type.",
  "Type de fichier non pris en charge.", "Nicht unterstützter Dateityp.", "Tipo de archivo no compatible.", "Tipo di file non supportato.",
  "未対応のファイル形式です。", "지원하지 않는 파일 형식입니다.", "Tipo de ficheiro não suportado.")
p("Up-and-down movement",
  "Mouvement haut–bas", "Auf-ab-Bewegung", "Movimiento arriba–abajo", "Movimento su–giù",
  "上下動", "상하 움직임", "Movimento cima–baixo")
p("Uploading and loading\u2026",
  "Téléversement et chargement\u2026", "Hochladen und Laden\u2026", "Subiendo y cargando\u2026", "Caricamento in corso\u2026",
  "アップロードと読み込み中\u2026", "업로드 및 로딩 중\u2026", "A enviar e a carregar\u2026")
p("Upper body down the fall line",
  "Haut du corps face à la ligne de pente", "Oberkörper in die Falllinie", "Tronco hacia la línea de máxima pendiente", "Busto verso la linea di massima pendenza",
  "上体はフォールライン方向", "상체는 폴라인 방향", "Tronco na linha de máxima pendente")
p("Upper-body rotation",
  "Rotation du haut du corps", "Oberkörperdrehung", "Rotación del tronco", "Rotazione del busto",
  "上体回旋", "상체 회전", "Rotação do tronco")
p("Upper-lower separation",
  "Séparation haut–bas", "Ober–Unter-Trennung", "Separación arriba–abajo", "Separazione alto–basso",
  "上下分離", "상하 분리", "Separação cima–baixo")
p("Usable frames",
  "Images exploitables", "Nutzbare Frames", "Fotogramas usables", "Frame utilizzabili",
  "有効フレーム", "사용 가능 프레임", "Fotogramas utilizáveis")
p("View",
  "Vue", "Ansicht", "Vista", "Vista",
  "ビュー", "뷰", "Vista")
p("View angle {deg:.0f}\u00b0",
  "Angle de vue {deg:.0f}\u00b0", "Blickwinkel {deg:.0f}\u00b0", "Ángulo de vista {deg:.0f}\u00b0", "Angolo di vista {deg:.0f}\u00b0",
  "撮影角 {deg:.0f}\u00b0", "시야각 {deg:.0f}\u00b0", "Ângulo de vista {deg:.0f}\u00b0")
p("Visual Pose",
  "Visual Pose", "Visual Pose", "Visual Pose", "Visual Pose",
  "Visual Pose", "Visual Pose", "Visual Pose")
p("Visual Pose \u2014 Windows",
  "Visual Pose \u2014 Windows", "Visual Pose \u2014 Windows", "Visual Pose \u2014 Windows", "Visual Pose \u2014 Windows",
  "Visual Pose \u2014 Windows", "Visual Pose \u2014 Windows", "Visual Pose \u2014 Windows")
p("Warning",
  "Avertissement", "Warnung", "Advertencia", "Avviso",
  "警告", "경고", "Aviso")
p("Weakest checkpoint",
  "Point de contrôle le plus faible", "Schwächster Checkpoint", "Checkpoint más débil", "Checkpoint più debole",
  "最も弱いチェックポイント", "가장 약한 체크포인트", "Checkpoint mais fraco")
p("Wedge angle",
  "Angle de chasse-neige", "Pflugwinkel", "Ángulo de cuña", "Angolo di spazzaneve",
  "プルーク角", "플루크 각도", "Ângulo de cunha")
p("Wedge christie",
  "Christie en chasse-neige", "Pflugchristie", "Christie en cuña", "Christie a spazzaneve",
  "プルーククリスティー", "플루크 크리스티", "Christie em cunha")
p("Wedge glide",
  "Glisse en chasse-neige", "Pfluggleiten", "Desliz en cuña", "Scivolata a spazzaneve",
  "プルークグライド", "플루크 글라이드", "Deslize em cunha")
p("Wedge stance",
  "Écartement en chasse-neige", "Pflug-Standbreite", "Base en cuña", "Base a spazzaneve",
  "プルークスタンス", "플루크 스탠스", "Base em cunha")
p("Wedge through the turn",
  "Chasse-neige pendant le virage", "Pflug durch den Schwung", "Cuña durante la curva", "Spazzaneve nella curva",
  "ターン中プルーク維持", "턴 중 플루크 유지", "Cunha durante a curva")
p("Wedge to start, close the inside ski to finish.",
  "Départ en chasse-neige, fermez le ski intérieur pour finir.",
  "Im Pflug starten, Innenski zum Abschluss schließen.",
  "Empieza en cuña y cierra el esquí interior al finalizar.",
  "Parti a spazzaneve e chiudi lo sci interno per finire.",
  "プルークで入り、仕上げで内側スキーを寄せる。",
  "플루크로 시작해 마무리에서 안쪽 스키를 모으세요.",
  "Comece em cunha e feche o ski interior para terminar.")
p("Wedge to start, gradually match at the finish; do not snap shut.",
  "Départ en chasse-neige, rapprochez progressivement à la fin ; ne claquez pas.",
  "Im Pflug starten, zum Ende allmählich parallel; nicht zuschlagen.",
  "Empieza en cuña y iguala poco a poco al final; no cierres de golpe.",
  "Parti a spazzaneve e avvicina gradualmente in uscita; non chiudere di scatto.",
  "プルークで入り、仕上げで徐々に揃える。急に閉じない。",
  "플루크로 시작해 마무리에서 서서히 맞추세요. 갑자기 닫지 마세요.",
  "Comece em cunha e iguale gradualmente no fim; não feche de chofre.")
p("Wedge turns",
  "Virages en chasse-neige", "Pflugschwünge", "Curvas en cuña", "Curve a spazzaneve",
  "プルークターン", "플루크 턴", "Curvas em cunha")
p("Wedge-glide on a green run, then open the tails and edge to a stop.",
  "Glissez en chasse-neige sur piste verte, puis ouvrez les talons et carrez jusqu’à l’arrêt.",
  "Auf grüner Piste im Pflug gleiten, dann Enden öffnen und kanten bis zum Stopp.",
  "Desliza en cuña en pista verde, luego abre las colas y canta hasta parar.",
  "Scivola a spazzaneve su pista verde, poi apri le code e metti lama fino all’arresto.",
  "緑斜面でプルークグライド後、テールを開きエッジで停止。",
  "그린에서 플루크 글라이드 후 테일을 열고 엣지로 정지하세요.",
  "Deslize em cunha numa pista verde, depois abra as caudas e cante até parar.")
p("Weibo",
  "Weibo", "Weibo", "Weibo", "Weibo",
  "Weibo", "Weibo", "Weibo")
p("Weight",
  "Poids", "Gewicht", "Peso", "Peso",
  "体重", "체중", "Peso")
p("What the clip itself could tell us",
  "Ce que le clip lui-même peut nous dire", "Was der Clip selbst verraten kann", "Lo que el propio clip puede decirnos", "Cosa può dirci il clip stesso",
  "クリップ自体が示せること", "클립 자체가 알려줄 수 있는 것", "O que o próprio clip nos pode dizer")
p("Why",
  "Pourquoi", "Warum", "Por qué", "Perché",
  "理由", "이유", "Porquê")
p("Why it matters",
  "Pourquoi c’est important", "Warum es zählt", "Por qué importa", "Perché conta",
  "なぜ重要か", "왜 중요한가", "Porque é importante")
p("Why this stage",
  "Pourquoi ce niveau", "Warum diese Stufe", "Por qué este nivel", "Perché questo livello",
  "なぜこの段階か", "왜 이 단계인가", "Porque este nível")
p("Wrists below the shoulders.",
  "Poignets sous les épaules.", "Handgelenke unter den Schultern.", "Muñecas por debajo de los hombros.", "Polsi sotto le spalle.",
  "手首は肩より下。", "손목은 어깨보다 아래.", "Pulsos abaixo dos ombros.")
p("X",
  "X", "X", "X", "X",
  "X", "X", "X")
p("You have it when",
  "C’est acquis quand", "Du hast’s, wenn", "Lo tienes cuando", "Ce l’hai quando",
  "できたサイン", "달성 기준", "Temos quando")
p("YouTube",
  "YouTube", "YouTube", "YouTube", "YouTube",
  "YouTube", "YouTube", "YouTube")

out = Path("locales/_ski_locale_fills/part06.json")
out.write_text(json.dumps(T, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("wrote", len(T), "->", out)
