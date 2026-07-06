from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "src" / "data"
PUBLIC_BANK_DIR = ROOT / "public" / "question-bank"


@dataclass(frozen=True)
class SourcePdf:
    file: str
    exam_id: str
    exam_label: str
    subject: str
    subject_name: str
    test_date: str


PDFS = [
    SourcePdf(
        file="114年第二梯次中級AI應用規劃師第一科人工智慧技術應用與規劃(當次試題公告114_20251226000616.pdf",
        exam_id="114-2",
        exam_label="114 年第二梯次",
        subject="S1",
        subject_name="科目1 人工智慧技術應用與規劃",
        test_date="114-11-08",
    ),
    SourcePdf(
        file="114年第二梯次中級AI應用規劃師第三科機器學習技術與應用(當次試題公告114_20251226000650.pdf",
        exam_id="114-2",
        exam_label="114 年第二梯次",
        subject="S3",
        subject_name="科目3 機器學習技術與應用",
        test_date="114-11-08",
    ),
    SourcePdf(
        file="115年第一次中級AI應用規劃師_第一科_人工智慧技術應用與規劃_公告試題_20260615003359.pdf",
        exam_id="115-1",
        exam_label="115 年第一次",
        subject="S1",
        subject_name="科目1 人工智慧技術應用與規劃",
        test_date="115-05-23",
    ),
    SourcePdf(
        file="115年第一次中級AI應用規劃師_第三科_機器學習技術與應用_公告試題_20260615003428.pdf",
        exam_id="115-1",
        exam_label="115 年第一次",
        subject="S3",
        subject_name="科目3 機器學習技術與應用",
        test_date="115-05-23",
    ),
]


TOPIC_KEYWORDS = [
    ("NLP", ["NLP", "自然語言", "詞性", "Word2Vec", "BERT", "文本", "語言模型", "翻譯", "情感"]),
    ("電腦視覺", ["影像", "CNN", "YOLO", "Faster R-CNN", "分割", "人臉", "物件", "VGG", "ResNet", "ViT", "AOI"]),
    ("生成式 AI", ["生成式", "LLM", "Llama", "GPT", "LoRA", "SFT", "Prompt", "微調", "RAG", "Agent", "ReAct", "多代理人"]),
    ("多模態", ["多模態", "影像模態", "文本模態", "語音", "異質資料"]),
    ("模型評估", ["Accuracy", "Precision", "Recall", "F1", "ROC", "AUC", "混淆矩陣", "mAP", "IoU", "驗證集"]),
    ("導入與部署", ["導入", "部署", "MLOps", "CI/CD", "監控", "資料治理", "系統集成", "需求"]),
    ("治理與合規", ["隱私", "公平", "偏見", "合規", "差分隱私", "同態加密", "安全多方", "模型治理"]),
    ("數學與統計", ["機率", "統計", "假設檢定", "蒙地卡羅", "矩陣", "線性代數", "PCA", "LDA", "t-SNE", "殘差圖"]),
    ("最佳化", ["梯度", "Adam", "SGD", "學習率", "Momentum", "損失函數", "MSE", "MAE", "交叉熵", "Huber"]),
    ("傳統機器學習", ["K-means", "KNN", "Naive Bayes", "XGBoost", "GBDT", "邏輯迴歸", "線性迴歸", "SVM"]),
    ("特徵工程", ["特徵", "資料擴增", "標準化", "正規化", "資料洩漏", "交叉驗證", "類別不平衡"]),
    ("深度學習", ["神經網路", "Transformer", "Self-Attention", "池化", "Dropout", "Batch Normalization", "PyTorch", "TensorFlow"]),
]


FULLWIDTH = str.maketrans({
    "Ａ": "A",
    "Ｂ": "B",
    "Ｃ": "C",
    "Ｄ": "D",
    "．": ".",
})

OPTION_RE = re.compile(r"[\(（]\s*([ABCD])\s*[\)）]")
QUESTION_RE = re.compile(r"^(?:(?P<answer>[ABCD])\s+)?(?P<number>\d{1,2})[.]\s*(?P<text>.*)$")
ANSWER_ONLY_RE = re.compile(r"^[ABCD]$")
PAGE_RE = re.compile(r"第\s*(\d+)\s*頁，共\s*(\d+)\s*頁")


def run_pdftotext(pdf_path: Path) -> list[tuple[int, str]]:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        raise RuntimeError("pdftotext was not found. Install Poppler or add it to PATH.")

    info = subprocess.run(
        [shutil.which("pdfinfo") or "pdfinfo", str(pdf_path)],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    pages_match = re.search(r"Pages:\s+(\d+)", info)
    if not pages_match:
        raise RuntimeError(f"Unable to determine page count for {pdf_path.name}")

    pages: list[tuple[int, str]] = []
    for page in range(1, int(pages_match.group(1)) + 1):
        proc = subprocess.run(
            [pdftotext, "-f", str(page), "-l", str(page), str(pdf_path), "-"],
            check=True,
            text=True,
            capture_output=True,
        )
        pages.append((page, proc.stdout))
    return pages


def normalize_line(line: str) -> str:
    line = line.translate(FULLWIDTH)
    line = line.replace("\u3000", " ")
    line = PAGE_RE.sub("", line)
    line = re.sub(r"\s+", " ", line).strip()
    return line


def is_noise(line: str) -> bool:
    if not line:
        return True
    exact_noise = {
        "一、選擇題",
        "二、程式題",
        "答案",
        "題目",
        "答案 題目",
        "題目 答案",
    }
    if line in exact_noise:
        return True
    return any(
        marker in line
        for marker in [
            "AI 應用規劃師-中級能力鑑定【公告試題】",
            "第一科：人工智慧技術應用與規劃",
            "第三科：機器學習技術與應用",
            "考試日期：",
            "試題公告日期：",
        ]
    )


def all_options_seen(lines: list[str]) -> bool:
    text = "\n".join(lines)
    return len({match.group(1) for match in OPTION_RE.finditer(text)}) >= 4


def is_probable_context_start(line: str, previous_line: str) -> bool:
    starters = (
        "請依據",
        "請根據",
        "請回答",
        "下圖",
        "以下",
        "使用 ",
        "VGG16",
        "Iris",
        "某人工智慧",
        "某團隊",
        "某公司",
        "某研究",
        "研究人員",
        "工程師",
    )
    if line.startswith(starters):
        return True
    return previous_line.endswith(("。", "；", ";", "？", "?", ")", "）")) and not OPTION_RE.match(line)


def split_prompt_options(raw_text: str) -> tuple[str, dict[str, str]]:
    matches = list(OPTION_RE.finditer(raw_text))
    if not matches:
        return raw_text.strip(), {}

    prompt = raw_text[: matches[0].start()].strip()
    options: dict[str, str] = {}
    for idx, match in enumerate(matches):
        letter = match.group(1)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw_text)
        option_text = raw_text[start:end].strip()
        option_text = option_text.strip("；;。 \n")
        options[letter] = option_text
    return prompt, options


def infer_topic(text: str, subject: str) -> str:
    hits: list[tuple[int, str]] = []
    for topic, keywords in TOPIC_KEYWORDS:
        score = sum(text.lower().count(keyword.lower()) for keyword in keywords)
        if score:
            hits.append((score, topic))
    if hits:
        return sorted(hits, reverse=True)[0][1]
    return "AI 技術應用" if subject == "S1" else "機器學習基礎"


def has_figure_reference(text: str) -> bool:
    return bool(re.search(r"附圖|下圖|上圖|圖中|下方資訊|程式碼片段|程式碼中|附表", text))


def parse_pdf(source: SourcePdf) -> list[dict]:
    pdf_path = ROOT / source.file
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    questions: list[dict] = []
    current: dict | None = None
    pending_context: list[str] = []
    answer_buffer: str | None = None

    def finalize() -> None:
        nonlocal current
        if not current:
            return
        raw_text = "\n".join(current["lines"]).strip()
        prompt, options = split_prompt_options(raw_text)
        combined = f"{prompt}\n" + "\n".join(options.values())
        number = current["number"]
        questions.append(
            {
                "id": f"{source.exam_id}-{source.subject}-{number:02d}",
                "number": number,
                "answer": current["answer"],
                "prompt": prompt,
                "options": options,
                "topic": infer_topic(combined, source.subject),
                "hasFigureReference": has_figure_reference(raw_text),
                "source": {
                    "file": source.file,
                    "examId": source.exam_id,
                    "examLabel": source.exam_label,
                    "subject": source.subject,
                    "subjectName": source.subject_name,
                    "testDate": source.test_date,
                    "page": current["page"],
                },
            }
        )
        current = None

    for page_number, page_text in run_pdftotext(pdf_path):
        for original_line in page_text.splitlines():
            line = normalize_line(original_line)
            if is_noise(line):
                continue

            if ANSWER_ONLY_RE.match(line):
                answer_buffer = line
                continue

            match = QUESTION_RE.match(line)
            if match and (match.group("answer") or answer_buffer):
                answer = match.group("answer") or answer_buffer
                number = int(match.group("number"))
                if not (1 <= number <= 50):
                    continue
                finalize()
                start_text = match.group("text").strip()
                current = {
                    "number": number,
                    "answer": answer,
                    "page": page_number,
                    "lines": [*pending_context, start_text] if start_text else [*pending_context],
                }
                pending_context = []
                answer_buffer = None
                continue

            if current is None:
                pending_context.append(line)
                continue

            previous = current["lines"][-1] if current["lines"] else ""
            if all_options_seen(current["lines"]) and is_probable_context_start(line, previous):
                finalize()
                pending_context = [line]
            else:
                current["lines"].append(line)

    finalize()
    return questions


def write_outputs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_BANK_DIR.mkdir(parents=True, exist_ok=True)

    all_questions: list[dict] = []
    summaries = []
    for pdf in PDFS:
        parsed = parse_pdf(pdf)
        all_questions.extend(parsed)
        summaries.append(
            {
                "file": pdf.file,
                "examId": pdf.exam_id,
                "subject": pdf.subject,
                "count": len(parsed),
                "missingOptions": [q["id"] for q in parsed if len(q["options"]) != 4],
                "figureRefs": sum(1 for q in parsed if q["hasFigureReference"]),
            }
        )
        shutil.copy2(ROOT / pdf.file, PUBLIC_BANK_DIR / pdf.file)

    all_questions.sort(key=lambda q: (q["source"]["examId"], q["source"]["subject"], q["number"]))
    output = {
        "generatedAt": "2026-07-06",
        "targetExamDate": "2026-11-14",
        "questions": all_questions,
        "summaries": summaries,
    }
    (DATA_DIR / "questions.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    print(f"wrote {len(all_questions)} questions to {DATA_DIR / 'questions.json'}")


if __name__ == "__main__":
    write_outputs()
