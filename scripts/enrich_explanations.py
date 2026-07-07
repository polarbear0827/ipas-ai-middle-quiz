from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from generate_learning_questions import CONCEPTS, goal_label
except ModuleNotFoundError:
    from scripts.generate_learning_questions import CONCEPTS, goal_label


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "src" / "data" / "questions.json"
LETTERS = ["A", "B", "C", "D"]


@dataclass(frozen=True)
class Concept:
    subject: str
    topic: str
    section: str
    page: int
    term: str
    correct: str
    wrongs: tuple[str, str, str]
    scenario: str
    goal: str


TOPIC_PROFILES = {
    "NLP": {
        "scope": "文字資料的理解、轉換、擷取或生成",
        "checks": "語料來源、標註品質、語境、語言別、斷詞或 token 化方式，以及輸出是否能被業務流程使用",
        "mistake": "把文字分類、翻譯、摘要、情感判斷與語法分析混在一起",
        "memory": "先判斷輸入是不是文字，再判斷輸出是類別、實體、翻譯、摘要還是向量表示。",
    },
    "電腦視覺": {
        "scope": "影像中的類別、位置、像素區域或物件個體判斷",
        "checks": "影像解析度、標註框或遮罩品質、推論延遲、IoU/mAP/混淆矩陣與部署硬體限制",
        "mistake": "混淆影像分類、目標檢測、語義分割與實例分割的輸出粒度",
        "memory": "分類問是什麼，檢測問在哪裡，分割問哪些像素，實例分割還要分出不同個體。",
    },
    "生成式 AI": {
        "scope": "產生文字、影像、程式碼或結合工具完成任務",
        "checks": "知識來源、提示設計、微調資料、幻覺風險、權限控管、可追溯紀錄與人工作業流程",
        "mistake": "把生成、檢索、微調、代理人與模型壓縮視為同一件事",
        "memory": "生成式 AI 的考點常問內容怎麼產生、知識怎麼補、模型怎麼客製、風險怎麼控。",
    },
    "多模態": {
        "scope": "整合文字、影像、語音、結構化資料等不同資料型態",
        "checks": "各模態的對齊方式、缺漏模態處理、融合策略、標註一致性與跨模態輸出品質",
        "mistake": "只處理單一資料型態卻稱為多模態",
        "memory": "多模態的關鍵是跨資料型態對齊與融合，不是把多份資料放在同一個資料夾。",
    },
    "導入與部署": {
        "scope": "把 AI 從需求、資料、模型、驗證一路接到正式服務",
        "checks": "業務目標、資料可得性、驗收指標、API 整合、監控、權限、回滾與維運責任",
        "mistake": "只完成模型或 demo 就以為完成導入",
        "memory": "導入題要找完整流程：需求、資料、模型、驗證、部署、監控、責任分工。",
    },
    "治理與合規": {
        "scope": "AI 系統的隱私、公平性、資安、偏誤、可追溯與責任管理",
        "checks": "資料授權、敏感資料保護、群體公平性、錯誤紀錄、人工覆核、監控與合規要求",
        "mistake": "只看 accuracy 卻忽略高影響情境中的風險",
        "memory": "治理題看到個資、偏誤、金融醫療、人工覆核、紀錄與責任歸屬就要提高警覺。",
    },
    "數學與統計": {
        "scope": "用機率、分布、線性代數或統計推論描述資料與不確定性",
        "checks": "變數型態、分布假設、樣本數、顯著性、矩陣或向量表示，以及統計結論是否被過度解讀",
        "mistake": "把統計量或機率名詞當成模型功能",
        "memory": "數統題先分清楚：機率描述不確定性，分布描述資料生成，檢定描述證據強度。",
    },
    "最佳化": {
        "scope": "用損失函數、梯度、學習率與正則化調整模型參數",
        "checks": "目標函數、更新規則、學習率、收斂穩定、過擬合、驗證表現與超參數搜尋成本",
        "mistake": "把優化器、損失函數、評估指標與資料前處理混為一談",
        "memory": "最佳化題要問：優化什麼目標、怎麼更新、如何避免震盪、過擬合或搜尋成本過高。",
    },
    "傳統機器學習": {
        "scope": "表格、分類、迴歸、分群與可解釋模型的選型與限制",
        "checks": "監督/非監督、目標變數型態、特徵尺度、資料量、可解釋性、距離或樹模型假設",
        "mistake": "用同一個模型解所有分類、迴歸與分群問題",
        "memory": "先判斷任務是分類、迴歸或分群，再看模型假設與資料型態。",
    },
    "深度學習": {
        "scope": "神經網路架構、訓練穩定、表示學習與大型模型基礎",
        "checks": "架構適配、訓練/驗證落差、梯度、參數量、正則化、硬體成本與資料需求",
        "mistake": "只看模型名稱或層數，不看架構為何適合任務",
        "memory": "深度學習題常考 CNN 看局部空間、RNN/Transformer 看序列、正則化看泛化。",
    },
    "特徵工程": {
        "scope": "把原始資料清理、轉換、擴增與表示成模型可用特徵",
        "checks": "缺失值、離群值、尺度、類別編碼、資料洩漏、標註品質、不平衡與特徵可解釋性",
        "mistake": "先做全資料前處理或用測試資訊幫助訓練，造成資料洩漏",
        "memory": "特徵工程題先看資料是否乾淨、尺度是否合理、切分是否偷看答案。",
    },
    "模型評估": {
        "scope": "用合適指標與資料切分判斷模型是否能泛化",
        "checks": "訓練/驗證/測試切分、混淆矩陣、precision、recall、F1、AUC、錯誤成本與類別不平衡",
        "mistake": "只看 accuracy 或訓練集分數就判定模型可上線",
        "memory": "評估題要把指標和錯誤成本連起來：怕誤報看 precision，怕漏報看 recall。",
    },
    "機器學習基礎": {
        "scope": "機器學習任務、資料切分、泛化能力與基本建模流程",
        "checks": "任務定義、訓練資料、標籤、驗證方式、泛化風險與部署後資料變化",
        "mistake": "把模型訓練成功視為一定能在真實資料成功",
        "memory": "基礎題先抓輸入、輸出、標籤、訓練/測試切分與泛化能力。",
    },
}


NEGATIVE_PATTERNS = [
    r"下列[^？?。]*不正確",
    r"下列[^？?。]*錯誤",
    r"何者[^？?。]*不正確",
    r"何者[^？?。]*錯誤",
    r"哪一[^？?。]*不正確",
    r"哪一[^？?。]*錯誤",
    r"哪一[^？?。]*最不",
    r"何者[^？?。]*最不",
    r"不符合",
    r"不屬於",
    r"不適合",
    r"不適當",
]


INTENT_PATTERNS = [
    ("技術路徑", "技術選型"),
    ("應對策略", "處置策略"),
    ("記憶體有限", "資源限制選型"),
    ("主要目的", "目的辨識"),
    ("主要原因", "機制原因"),
    ("最適合", "情境選型"),
    ("最合理", "情境判斷"),
    ("符合", "條件對應"),
    ("差異", "概念比較"),
    ("評估", "模型評估"),
    ("部署", "部署維運"),
    ("監控", "部署維運"),
    ("資料", "資料條件"),
    ("何者", "概念辨識"),
]


DISTRACTOR_HINTS = [
    ("翻譯", "機器翻譯", "把一種語言轉成另一種語言"),
    ("摘要", "文字摘要", "濃縮內容重點"),
    ("情感", "情感分析", "判斷文字的正負或中立傾向"),
    ("詞性", "詞性標註", "標記名詞、動詞、形容詞等語法類別"),
    ("實體", "命名實體辨識", "擷取人名、地名、組織、金額等實體"),
    ("卷積", "CNN/卷積運算", "擷取影像局部空間特徵"),
    ("分割", "影像分割", "輸出像素層級區域"),
    ("邊界框", "目標檢測", "定位物件位置與類別"),
    ("強化學習", "強化學習", "透過獎勵回饋學習行動策略"),
    ("資料增強", "資料擴增", "用合理變換增加訓練樣本多樣性"),
    ("知識蒸餾", "知識蒸餾", "用大模型教小模型以壓縮或加速"),
    ("剪枝", "模型剪枝", "移除低重要性權重或結構"),
    ("LoRA", "LoRA", "凍結原權重並訓練低秩適配矩陣"),
    ("RAG", "RAG", "先檢索可信資料再生成回答"),
    ("Agent", "代理人流程", "讓模型結合推理與工具行動"),
    ("同態加密", "同態加密", "在密文上進行運算以保護資料"),
    ("差分隱私", "差分隱私", "加入噪聲降低個體資料被推知的風險"),
    ("聯邦學習", "聯邦學習", "資料留在本地、交換模型更新"),
    ("Precision", "Precision", "預測為正類者有多少是真的"),
    ("Recall", "Recall", "實際正類有多少被抓到"),
    ("Accuracy", "Accuracy", "整體預測正確比例"),
    ("F1", "F1-score", "平衡 precision 與 recall"),
    ("AUC", "AUC/ROC", "觀察不同門檻下的分類能力"),
    ("混淆矩陣", "混淆矩陣", "呈現 TP、FP、TN、FN 的錯誤結構"),
    ("資料洩漏", "資料洩漏", "訓練流程偷看到測試或未來資訊"),
    ("過擬合", "過擬合", "訓練好但泛化差"),
    ("欠擬合", "欠擬合", "訓練資料也學不好"),
]


SPECIAL_TARGETS = [
    {
        "term": "資料分布偏移監控",
        "topic": "導入與部署",
        "goal": "發現上線輸入資料已偏離訓練分布，及早偵測模型失準風險",
        "keywords": ["資料偏移", "資料漂移", "分佈已與原訓練集", "分布已與原訓練集", "輸入資料偏移"],
    },
    {
        "term": "線上持續監控",
        "topic": "導入與部署",
        "goal": "追蹤線上模型服務的資料、效能、延遲與錯誤狀態，維持上線品質",
        "keywords": ["Continuous Monitoring", "線上持續監控", "即時監控系統"],
    },
    {
        "term": "變分自編碼器（VAE）",
        "topic": "生成式 AI",
        "goal": "透過潛在空間建模資料分布，可用於生成、重建或分布異常觀察",
        "keywords": ["變分自編碼器", "VAE"],
    },
]


def normalize(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def compact(text: str | None) -> str:
    return normalize(text).lower()


def make_concepts() -> list[Concept]:
    rows: list[Concept] = []
    for item in CONCEPTS:
        subject, topic, section, page, term, correct, wrong1, wrong2, wrong3, scenario, goal = item
        rows.append(
            Concept(
                subject=subject,
                topic=topic,
                section=section,
                page=page,
                term=term,
                correct=correct,
                wrongs=(wrong1, wrong2, wrong3),
                scenario=scenario,
                goal=goal_label(goal),
            )
        )
    return rows


CONCEPT_ROWS = make_concepts()


def special_target(question: dict) -> dict | None:
    text = normalize(question.get("prompt", "") + " " + option_text(question, question.get("answer")))
    for target in SPECIAL_TARGETS:
        if any(keyword in text for keyword in target["keywords"]):
            return target
    return None


def option_text(question: dict, letter: str) -> str:
    return normalize(question.get("options", {}).get(letter, ""))


def is_negative_question(prompt: str) -> bool:
    text = normalize(prompt)
    return any(re.search(pattern, text) for pattern in NEGATIVE_PATTERNS)


def infer_intent(prompt: str) -> str:
    for pattern, label in INTENT_PATTERNS:
        if pattern in prompt:
            return label
    return "概念應用"


def quoted_terms(prompt: str) -> list[str]:
    return [item for item in re.findall(r"「([^」]{2,40})」", prompt) if len(item.strip()) >= 2]


def concept_score(question: dict, concept: Concept) -> int:
    source = question.get("source", {})
    subject = source.get("subject")
    topic = question.get("topic")
    prompt_text = compact(question.get("prompt", ""))
    answer_text = compact(option_text(question, question.get("answer")))
    wrong_text = compact(" ".join(option_text(question, letter) for letter in LETTERS if letter != question.get("answer")))
    term = compact(concept.term)
    score = 0
    evidence = 0
    if subject == concept.subject:
        score += 5
    if topic == concept.topic:
        score += 5
    if term and term in prompt_text:
        score += 30
        evidence += 30
    if term and term in answer_text:
        score += 28
        evidence += 28
    if term and term in wrong_text:
        score += 3
    for part in re.split(r"[ /\-()（）]+", concept.term):
        part = compact(part)
        if len(part) >= 3 and part in prompt_text:
            score += 8
            evidence += 8
        elif len(part) >= 3 and part in answer_text:
            score += 8
            evidence += 8
    if compact(concept.correct) == answer_text:
        score += 36
        evidence += 36
    elif compact(concept.correct) and compact(concept.correct) in answer_text:
        score += 20
        evidence += 20
    elif answer_text and answer_text in compact(concept.correct):
        score += 12
        evidence += 12
    if compact(concept.goal) and compact(concept.goal) in (prompt_text + " " + answer_text):
        score += 12
        evidence += 12
    if compact(concept.scenario) and compact(concept.scenario) in prompt_text:
        score += 8
        evidence += 8
    return score if evidence >= 10 else 0


def match_concept(question: dict) -> tuple[Concept | None, int]:
    scored = sorted(((concept_score(question, c), c) for c in CONCEPT_ROWS), key=lambda item: item[0], reverse=True)
    best_score, best = scored[0]
    if best_score >= 18:
        return best, best_score
    return None, best_score


def infer_term(question: dict, concept: Concept | None) -> str:
    special = special_target(question)
    if special and (concept is None or compact(concept.term) not in compact(option_text(question, question.get("answer")))):
        return special["term"]
    if concept:
        return concept.term
    prompt = normalize(question.get("prompt", ""))
    answer = option_text(question, question.get("answer"))
    quotes = quoted_terms(prompt)
    if quotes:
        return quotes[-1]
    tech_match = re.search(r"([\u4e00-\u9fffA-Za-z0-9 \-]{2,22})[（(]([A-Za-z0-9 /+\-.]+)[）)]", answer)
    if tech_match:
        chinese = normalize(tech_match.group(1)).split()[-1]
        english = normalize(tech_match.group(2))
        return f"{chinese}（{english}）"
    prompt_text = compact(prompt)
    answer_text = compact(answer)
    prompt_candidates = []
    answer_candidates = []
    for row in CONCEPT_ROWS:
        term = compact(row.term)
        if term and term in prompt_text:
            prompt_candidates.append(row.term)
        if term and term in answer_text:
            answer_candidates.append(row.term)
    if prompt_candidates:
        return sorted(prompt_candidates, key=len, reverse=True)[0]
    if answer_candidates:
        return sorted(answer_candidates, key=len, reverse=True)[0]
    return question.get("topic") or "本概念"


def profile_for(question: dict, concept: Concept | None) -> dict:
    special = special_target(question)
    if special:
        return TOPIC_PROFILES.get(special["topic"], TOPIC_PROFILES["機器學習基礎"])
    if concept and concept.topic in TOPIC_PROFILES:
        return TOPIC_PROFILES[concept.topic]
    return TOPIC_PROFILES.get(question.get("topic"), TOPIC_PROFILES["機器學習基礎"])


def source_position(question: dict, concept: Concept | None) -> str:
    source = question.get("source", {})
    subject_name = source.get("subjectName", "中級 AI 應用規劃師")
    if source.get("examId") == "GUIDE":
        section = source.get("section") or (concept.section if concept else "")
        section_text = f" 第 {section} 節" if section else ""
        return f"學習指引定位：{subject_name}{section_text}，主題「{question.get('topic')}」。"
    guide_text = ""
    if concept:
        guide_text = f"；可對照學習指引第 {concept.section} 節「{concept.term}」"
    return f"官方題定位：{source.get('examLabel')} {subject_name}，抽題分類「{question.get('topic')}」{guide_text}。"


def concise_prompt(prompt: str) -> str:
    text = normalize(prompt)
    if len(text) <= 96:
        return text
    return text[:92] + "..."


def detect_distractor(text: str, target_term: str) -> tuple[str, str] | None:
    clean = compact(text)
    for keyword, name, meaning in DISTRACTOR_HINTS:
        if compact(keyword) in clean and compact(keyword) not in compact(target_term):
            return name, meaning
    for row in CONCEPT_ROWS:
        term = compact(row.term)
        if len(term) >= 3 and term in clean and term not in compact(target_term):
            return row.term, row.goal
    return None


def negative_conflict_reason(prompt: str, text: str, term: str) -> str:
    if "正規化" in text and any(word in prompt for word in ["族群", "語言", "文化", "語氣", "偏誤"]):
        return (
            "題幹描述的是不同語言、族群與語氣造成的資料代表性與偏誤問題；"
            "詞嵌入正規化主要處理向量尺度或距離穩定，不能直接解釋文化語境與標註偏差。"
        )
    if "離線" in prompt and any(word in text for word in ["即時", "線上", "監控"]):
        return "題幹要求找出不適合即時監控、應放到離線實驗追蹤的項目；這個選項和監控時效要求不一致。"
    if "過擬合" in prompt and any(word in text for word in ["增加", "加深", "更多", "擴大"]):
        return "題幹在問降低模型複雜度或限制學習能力；增加容量或訓練自由度通常不是防止過擬合的方向。"
    if "多代理人" in prompt and any(word in text for word in ["忽略", "不需", "直接接受", "無條件"]):
        return "多代理人系統需要協調、驗證與容錯；無條件接受或忽略低品質結果會破壞任務可靠性。"
    return f"它和題幹條件或正確流程衝突，會讓「{term}」偏離原本要解決的任務。"


def option_reason(
    question: dict,
    letter: str,
    concept: Concept | None,
    term: str,
    profile: dict,
    negative: bool,
) -> str:
    answer = question.get("answer")
    text = option_text(question, letter)
    answer_text = option_text(question, answer)
    if letter == answer:
        if negative:
            conflict = negative_conflict_reason(normalize(question.get("prompt", "")), text, term)
            return (
                f"{letter}. {text}：這一項正是題幹要求找出的問題選項。{conflict}"
                "考試看到反向題時，要把答案理解成「最不該採用的作法」。"
            )
        special = special_target(question)
        concept_goal = special["goal"] if special and term == special["term"] else (concept.goal if concept else profile["scope"])
        return (
            f"{letter}. {text}：這是正解，因為它直接回應題幹中的任務條件，並且符合「{term}」的核心：{concept_goal}。"
            f"它不是只堆名詞，而是把輸入、處理方式與預期輸出連起來。"
        )

    if negative:
        special = special_target(question)
        if special and term == special["term"]:
            return (
                f"{letter}. {text}：這反而屬於「{term}」可以追蹤或治理的合理項目，"
                f"因此不是題幹要排除的答案；反向題要找的是最不符合「{special['goal']}」的選項。"
            )
        return (
            f"{letter}. {text}：這個選項雖然可能有風險或限制，但不是本題最關鍵的錯誤點。"
            f"反向題要找的是與題幹條件最直接衝突的選項；相較之下，正解 {answer} 的問題更明確。"
        )

    distractor = detect_distractor(text, term)
    if distractor:
        name, meaning = distractor
        return (
            f"{letter}. {text}：這比較像在描述「{name}」，重點是{meaning}；"
            f"但本題問的是「{term}」，因此輸入、輸出或應用目的沒有對準題幹。"
        )
    if any(word in text for word in ["一定", "完全", "所有", "保證", "無需", "不需要"]):
        return (
            f"{letter}. {text}：這類絕對化說法通常太危險。AI 應用要看資料品質、任務限制與評估結果，"
            f"不能因為使用「{term}」就保證成功。"
        )
    if "只" in text:
        return (
            f"{letter}. {text}：這把問題過度簡化。{profile['scope']}通常還要同時考慮資料條件、模型輸出、"
            f"驗證指標與維運限制，不能只靠單一步驟判斷。"
        )
    if answer_text and len(text) > len(answer_text) * 1.7:
        return (
            f"{letter}. {text}：文字較完整不代表正確。這個選項混入了額外條件，沒有精準回答題幹要問的「{term}」主軸。"
        )
    return (
        f"{letter}. {text}：這個說法可能碰到相關領域，但沒有抓住本題關鍵。題目要你辨識的是「{term}」如何對應"
        f"「{profile['scope']}」，而不是選一個看起來也像 AI 的描述。"
    )


def build_deep_explanation(question: dict) -> str:
    concept, _score = match_concept(question)
    special = special_target(question)
    if special and concept and compact(concept.term) not in compact(option_text(question, question.get("answer"))):
        concept = None
    term = infer_term(question, concept)
    profile = profile_for(question, concept)
    prompt = normalize(question.get("prompt", ""))
    answer = question.get("answer")
    answer_text = option_text(question, answer)
    negative = is_negative_question(prompt)
    intent = infer_intent(prompt)
    goal = special["goal"] if special and term == special["term"] else (concept.goal if concept else profile["scope"])
    section_lines = [
        "深度解析",
        source_position(question, concept),
        "",
        f"本題在考什麼：這是一題「{intent}」題。題幹線索是「{concise_prompt(prompt)}」；作答時要先判斷題目要的輸出、限制與成功標準，再把它對回「{term}」。",
    ]
    if negative:
        section_lines.append(
            f"正解判斷：答案 {answer} 不是一般正向最佳作法，而是題幹要求找出的不正確或最不適合選項。選項內容為「{answer_text}」，它與「{term}」應該滿足的條件衝突。"
        )
    else:
        section_lines.append(
            f"正解判斷：答案 {answer}「{answer_text}」最能對準本題。它符合「{term}」的核心目的：{goal}，也能回應題幹中給出的應用情境。"
        )
    section_lines.extend(
        [
            "",
            "選項逐一拆解：",
            *[option_reason(question, letter, concept, term, profile, negative) for letter in LETTERS],
            "",
            f"實務延伸：如果把這題放到真實專案，不只要選對名詞，還要檢查{profile['checks']}。常見陷阱是{profile['mistake']}，這會讓模型看似可用，實際上卻無法驗收或部署。",
            f"考前記憶點：{profile['memory']}",
        ]
    )
    if question.get("hasFigureReference"):
        section_lines.append("圖表提醒：這題原題含圖表、程式碼或頁面參照；刷題時先用文字判斷概念，考前再回 PDF 核對數值或圖中細節。")
    return "\n".join(section_lines)


def enrich(data: dict) -> dict:
    questions = data.get("questions", [])
    for question in questions:
        question["explanation"] = build_deep_explanation(question)
    data["explanationVersion"] = "deep-v2-2026-07-07"
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Add deep per-question explanations to the iPAS quiz bank.")
    parser.add_argument("--preview", type=int, default=0, help="Print the first N enriched explanations without writing.")
    args = parser.parse_args()

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    enriched = enrich(data)
    if args.preview:
        for question in enriched["questions"][: args.preview]:
            print("=" * 80)
            print(question["id"], question["topic"], "answer", question["answer"])
            print(question["explanation"])
        return
    DATA_FILE.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"enriched={len(enriched['questions'])} version={enriched['explanationVersion']}")


if __name__ == "__main__":
    main()
