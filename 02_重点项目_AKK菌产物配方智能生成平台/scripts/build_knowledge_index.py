from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "mock" / "literature_knowledge_items.json"
CHUNK_OUTPUT_PATH = ROOT / "data" / "mock" / "literature_knowledge_chunks.json"
VECTOR_DIM = 384


SOURCE_DIR_HINTS = ["akk菌资料", "安全性评价"]

TOPIC_RULES = [
    ("safety", ["安全", "毒理", "遗传毒性", "亚慢性", "noael", "toxicity", "safe"]),
    ("clinical", ["临床", "人体", "志愿者", "随机", "安慰剂", "超重", "肥胖", "糖尿病", "human", "clinical"]),
    ("regulatory", ["法规", "fda", "ndi", "novel food", "efsa", "备案", "欧盟"]),
    ("patent", ["专利", "patent"]),
    ("dairy_matrix", ["牛奶", "脱脂乳", "酸奶", "发酵乳", "乳", "milk", "dairy", "yogurt"]),
    ("postbiotic", ["后生元", "灭活", "巴氏", "pasteurized", "heat-killed", "postbiotic"]),
    ("metabolite", ["代谢", "脂质组", "代谢组", "短链脂肪酸", "scfa", "metabol"]),
    ("fiber_polysaccharide", ["膳食纤维", "多糖", "桔梗", "纤维", "菊粉", "fiber", "polysaccharide"]),
    ("culture_condition", ["培养", "分离", "生长", "反应器", "厌氧", "culture", "growth"]),
    ("mechanism", ["机制", "外膜蛋白", "amuc", "屏障", "黏液", "炎症", "免疫", "tlr2", "barrier"]),
    ("food_application", ["食品", "复配", "配方", "发酵", "应用", "food"]),
    ("weight_metabolism", ["减重", "肥胖", "体重", "血糖", "脂代谢", "代谢综合征", "weight", "glucose"]),
]

EXTERNAL_SEED_ITEMS = [
    {
        "knowledgeId": "seed-efsa-2021-pasteurized-akk",
        "title": "EFSA 2021：巴氏灭活 Akkermansia muciniphila 作为新食品的安全性意见",
        "sourceName": "EFSA Journal",
        "sourceUrl": "https://efsa.onlinelibrary.wiley.com/doi/full/10.2903/j.efsa.2021.6780",
        "sourceFile": None,
        "year": 2021,
        "evidenceType": "regulatory",
        "evidenceLevel": "A",
        "topics": ["safety", "regulatory", "postbiotic"],
        "foodMatrix": ["supplement"],
        "akkMaterial": ["pasteurized_akk_or_postbiotic"],
        "summary": "EFSA 对巴氏灭活 A. muciniphila 作为新食品进行了安全性评估，可作为研发阶段的安全边界和合规表达参考。",
        "usableInsights": [
            "适合作为巴氏灭活 AKK 或后生元方向的安全边界证据。",
            "配方结果中应避免把安全意见直接转化为疾病治疗或最终上市承诺。",
        ],
        "riskNotes": [
            "不同国家和食品类别的合规要求不同，商业化前必须进行目标市场法规复核。",
            "研发平台只能生成实验建议，不能替代法规审查和人体功效验证。",
        ],
        "validationMetrics": ["法规适用性复核", "安全性资料复核", "标签宣称边界审查"],
        "textPreview": "Pasteurised Akkermansia muciniphila was assessed as a novel food safety case by EFSA.",
    },
    {
        "knowledgeId": "seed-efsa-2025-extension",
        "title": "EFSA 2025：巴氏灭活 Akkermansia muciniphila 扩展使用人群的安全性意见",
        "sourceName": "EFSA Journal",
        "sourceUrl": "https://efsa.onlinelibrary.wiley.com/doi/10.2903/j.efsa.2025.9632",
        "sourceFile": None,
        "year": 2025,
        "evidenceType": "regulatory",
        "evidenceLevel": "A",
        "topics": ["safety", "regulatory", "postbiotic", "clinical"],
        "foodMatrix": ["supplement", "fsmp"],
        "akkMaterial": ["pasteurized_akk_or_postbiotic"],
        "summary": "EFSA 对巴氏灭活 AKK 的扩展使用提出安全性意见，适合用于平台对不同目标人群的风险提示。",
        "usableInsights": [
            "当目标商品涉及青少年、孕产妇等敏感人群时，应自动提高安全和法规审核优先级。",
            "可支撑平台在方案建议书中显示“人群适用性需复核”的提示。",
        ],
        "riskNotes": ["敏感人群应用不能仅凭平台建议推进，需要独立法规、伦理和临床证据评估。"],
        "validationMetrics": ["目标人群合规复核", "安全边界审核", "用量边界确认"],
        "textPreview": "The extension of use concerned food supplements and FSMPs for additional population groups.",
    },
    {
        "knowledgeId": "seed-amuc1100-nature-medicine",
        "title": "Amuc_1100 外膜蛋白：耐巴氏热处理并与 TLR2、肠屏障改善相关",
        "sourceName": "Nature Medicine / related article",
        "sourceUrl": "https://www.natap.org/2017/HIV/nm.4236.pdf",
        "sourceFile": None,
        "year": 2017,
        "evidenceType": "mechanism_or_basic_research",
        "evidenceLevel": "B",
        "topics": ["mechanism", "postbiotic", "safety"],
        "foodMatrix": [],
        "akkMaterial": ["amuc_1100_or_outer_membrane_protein", "pasteurized_akk_or_postbiotic"],
        "summary": "研究指出 Amuc_1100 是 A. muciniphila 外膜相关蛋白，具有热稳定特征，并与 TLR2、肠屏障改善等机制相关。",
        "usableInsights": [
            "可解释为什么平台在酸奶、饮料或粉剂方案中优先考虑后生元粉末与热稳定标志物保留。",
            "适合用于“肠道屏障概念”“后生元概念”的机制理由，但不能直接等同于人体功效。",
        ],
        "riskNotes": ["机制证据不等于目标商品功效，需要通过目标基质中的标志物保留、感官和稳定性实验验证。"],
        "validationMetrics": ["Amuc_1100 或相关标志物保留率", "热处理前后对比", "酸性体系稳定性"],
        "textPreview": "Amuc_1100 has been reported as a heat-stable outer membrane protein interacting with TLR2 and gut barrier pathways.",
    },
    {
        "knowledgeId": "seed-yogurt-postbiotic-pubmed-2025",
        "title": "酸奶基质中添加 AKK 后生元的人群研究线索",
        "sourceName": "PubMed",
        "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/40451504/",
        "sourceFile": None,
        "year": 2025,
        "evidenceType": "human_clinical",
        "evidenceLevel": "B",
        "topics": ["clinical", "dairy_matrix", "postbiotic", "weight_metabolism", "food_application"],
        "foodMatrix": ["dairy", "yogurt"],
        "akkMaterial": ["pasteurized_akk_or_postbiotic"],
        "summary": "公开摘要显示，含 AKK 后生元的乳制品/酸奶方向已有面向体重管理和肝酶指标的人群研究线索，但仍需进一步确认。",
        "usableInsights": [
            "可作为低糖酸奶、轻负担酸奶、体重管理概念样品的方向性证据。",
            "推荐平台把“酸性乳基稳定性、口感、标志物保留”列为首轮必测项。",
        ],
        "riskNotes": ["该类研究不能直接支持疾病治疗宣称，也不能替代目标产品自身的人体或稳定性验证。"],
        "validationMetrics": ["酸奶体系稳定性", "感官接受度", "标志物保留率", "货架期浊度/析水观察"],
        "textPreview": "A dairy product enriched with Akkermansia muciniphila postbiotic was reported with favorable exploratory effects, requiring further confirmation.",
    },
]


def normalize(text: str) -> str:
    return text.lower().replace("_", " ").replace("-", " ")


def source_dirs() -> list[Path]:
    dirs: list[Path] = []
    for child in ROOT.iterdir():
        if child.is_dir() and any(hint in child.name for hint in SOURCE_DIR_HINTS):
            dirs.append(child)
    return dirs


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def read_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(path))
            pages = [(page.extract_text() or "") for page in reader.pages[:30]]
            return clean_text(" ".join(pages))
        except Exception as exc:
            return f"PDF 正文抽取失败：{exc}"
    if suffix in {".txt", ".md"}:
        return clean_text(path.read_text(encoding="utf-8", errors="ignore"))
    return ""


def clean_title(path: Path) -> str:
    name = re.sub(r"[_\s]+", " ", path.stem)
    return re.sub(r"\s+", " ", name).strip()


def detect_topics(text: str) -> list[str]:
    normalized = normalize(text)
    topics = [topic for topic, keywords in TOPIC_RULES if any(keyword.lower() in normalized for keyword in keywords)]
    return topics or ["akk_general"]


def detect_year(text: str) -> int | None:
    years = [int(match) for match in re.findall(r"(20[0-3]\d)", text)]
    return max(years) if years else None


def detect_evidence_type(topics: list[str], text: str) -> str:
    normalized = normalize(text)
    if "regulatory" in topics:
        return "regulatory"
    if "clinical" in topics:
        return "human_clinical"
    if "safety" in topics:
        return "toxicology_safety"
    if "patent" in topics:
        return "patent"
    if "food_application" in topics or "dairy_matrix" in topics:
        return "food_application"
    if "culture_condition" in topics:
        return "strain_culture"
    if "综述" in normalized or "review" in normalized:
        return "review"
    return "mechanism_or_basic_research"


def evidence_level(evidence_type: str, topics: list[str]) -> str:
    if evidence_type == "regulatory":
        return "A"
    if evidence_type == "toxicology_safety":
        return "A"
    if evidence_type == "human_clinical":
        return "B"
    if evidence_type == "food_application":
        return "B"
    if evidence_type in {"mechanism_or_basic_research", "strain_culture", "review"}:
        return "C"
    return "D"


def food_matrix(topics: list[str], text: str) -> list[str]:
    normalized = normalize(text)
    matrices = []
    if "dairy_matrix" in topics:
        matrices.append("dairy")
    if any(keyword in normalized for keyword in ["酸奶", "发酵乳", "yogurt"]):
        matrices.append("yogurt")
    if any(keyword in normalized for keyword in ["牛奶", "脱脂乳", "milk"]):
        matrices.append("milk")
    if any(keyword in normalized for keyword in ["饮料", "beverage", "即饮"]):
        matrices.append("functional_beverage")
    if any(keyword in normalized for keyword in ["粉", "代餐", "营养"]):
        matrices.append("nutrition_powder")
    return sorted(set(matrices))


def akk_material(topics: list[str], text: str) -> list[str]:
    normalized = normalize(text)
    materials = []
    if "postbiotic" in topics:
        materials.append("pasteurized_akk_or_postbiotic")
    if "metabolite" in topics:
        materials.append("akk_metabolites")
    if "fiber_polysaccharide" in topics:
        materials.append("fiber_or_polysaccharide_related")
    if "amuc" in normalized or "外膜蛋白" in normalized:
        materials.append("amuc_1100_or_outer_membrane_protein")
    if not materials:
        materials.append("akk_related_material")
    return materials


def extract_sentences(text: str, keywords: list[str], max_items: int = 4) -> list[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[。！？.!?])\s+|；|;", text)
    hits = []
    for part in parts:
        clean = part.strip()
        if len(clean) < 30:
            continue
        lowered = clean.lower()
        if any(keyword.lower() in lowered for keyword in keywords):
            hits.append(clean[:360])
        if len(hits) >= max_items:
            break
    return hits


def build_summary(title: str, evidence_type: str, topics: list[str], extracted_text: str) -> str:
    keywords = ["Akkermansia", "muciniphila", "AKK", "安全", "毒理", "酸奶", "牛奶", "代谢", "纤维", "多糖", "Amuc"]
    sentences = extract_sentences(extracted_text, keywords, max_items=2)
    if sentences:
        return f"已读取论文正文并抽取证据。资料类型为 {evidence_type}，主题包括 {', '.join(topics)}。关键片段：{' '.join(sentences)}"
    return f"已纳入资料：{title}。资料类型为 {evidence_type}，主题包括 {', '.join(topics)}。正文抽取不足时，系统将降低证据权重。"


def insight_for(topics: list[str], evidence_type: str, matrices: list[str]) -> list[str]:
    insights = []
    if "dairy_matrix" in topics or {"dairy", "yogurt", "milk"}.intersection(matrices):
        insights.append("可用于乳基、酸奶、发酵乳或复配牛奶方向的配方证据筛选。")
    if "postbiotic" in topics:
        insights.append("支持巴氏灭活 AKK、后生元概念、热稳定标志物保留方向的研发假设。")
    if "fiber_polysaccharide" in topics:
        insights.append("可用于膳食纤维、多糖、饱腹感、质构和 AKK 生长/代谢关联方向。")
    if "metabolite" in topics:
        insights.append("可用于解释 AKK 代谢产物、风味负载、脂代谢或代谢组学相关方案。")
    if evidence_type == "human_clinical":
        insights.append("可作为人体研究背景，但不能直接替代目标商品自身功效验证。")
    if evidence_type == "toxicology_safety":
        insights.append("可作为安全性边界、毒理评价和研发合规提醒的高优先级依据。")
    if evidence_type == "regulatory":
        insights.append("可作为法规路径、申报状态和上市表达边界的强制引用依据。")
    if evidence_type == "patent":
        insights.append("可用于竞品和专利空间分析，但不能单独作为科学有效性证据。")
    return insights or ["可作为 AKK 研发资料库中的背景证据，需结合具体食品基质和实验条件使用。"]


def risk_for(topics: list[str], evidence_type: str) -> list[str]:
    risks = ["所有结论仅用于内部研发建议，不能直接作为上市配方或功效宣称。"]
    if evidence_type in {"mechanism_or_basic_research", "review", "patent"}:
        risks.append("该类资料不能直接证明目标食品产品的人体功效，需要实验验证和合规审查。")
    if "dairy_matrix" in topics:
        risks.append("乳基或酸性体系需要重点验证酸稳定性、感官影响、浊度变化和标志物保留。")
    if "clinical" in topics or "weight_metabolism" in topics:
        risks.append("涉及体重、血糖、脂代谢等表达时，应避免疾病治疗或确定性功效承诺。")
    if "regulatory" in topics:
        risks.append("不同国家和地区法规要求不同，实际商业化需要目标市场法规复核。")
    return risks


def validation_for(topics: list[str], matrices: list[str]) -> list[str]:
    metrics = ["关键标志物保留率", "感官接受度"]
    if {"dairy", "yogurt", "milk"}.intersection(matrices):
        metrics.extend(["酸性体系稳定性", "浊度变化", "析水率", "货架期稳定性"])
    if "nutrition_powder" in matrices:
        metrics.extend(["复水时间", "粉体流动性", "分散性"])
    if "fiber_polysaccharide" in topics:
        metrics.extend(["黏度变化", "饱腹感小试评价"])
    if "safety" in topics or "regulatory" in topics:
        metrics.extend(["安全性资料复核", "标签与宣称合规审查"])
    return sorted(set(metrics))


def source_name(path: Path) -> str:
    try:
        return str(path.parent.relative_to(ROOT))
    except ValueError:
        return path.parent.name


def chunk_text(text: str, max_chars: int = 720, overlap: int = 120) -> list[str]:
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end].strip()
        if len(chunk) >= 80:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks[:12]


def feature_tokens(text: str) -> Iterable[str]:
    normalized = normalize(text)
    for token in re.findall(r"[a-z0-9_]{2,}|[\u4e00-\u9fff]{2,}", normalized):
        yield token
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
    for index in range(max(len(chinese) - 1, 0)):
        yield chinese[index : index + 2]
    for topic, keywords in TOPIC_RULES:
        if any(keyword.lower() in normalized for keyword in keywords):
            yield f"topic:{topic}"


def hashed_embedding(text: str) -> list[float]:
    vector = [0.0] * VECTOR_DIM
    for token in feature_tokens(text):
        bucket = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16) % VECTOR_DIM
        vector[bucket] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [round(value / norm, 6) for value in vector]


def build_item(path: Path, index: int, extracted_text: str) -> dict:
    title = clean_title(path)
    evidence_text = f"{title} {extracted_text[:3000]}"
    topics = detect_topics(evidence_text)
    year = detect_year(evidence_text)
    evidence_type = detect_evidence_type(topics, evidence_text)
    level = evidence_level(evidence_type, topics)
    matrices = food_matrix(topics, evidence_text)
    return {
        "knowledgeId": f"lit-{index:04d}",
        "title": title,
        "sourceName": source_name(path),
        "sourceUrl": f"local://{path.relative_to(ROOT).as_posix()}",
        "sourceFile": str(path.relative_to(ROOT)),
        "year": year,
        "evidenceType": evidence_type,
        "evidenceLevel": level,
        "topics": topics,
        "foodMatrix": matrices,
        "akkMaterial": akk_material(topics, evidence_text),
        "summary": build_summary(title, evidence_type, topics, extracted_text),
        "textPreview": extracted_text[:420],
        "usableInsights": insight_for(topics, evidence_type, matrices),
        "riskNotes": risk_for(topics, evidence_type),
        "validationMetrics": validation_for(topics, matrices),
    }


def build_chunks(item: dict, extracted_text: str) -> list[dict]:
    fallback = "。".join(
        [
            item["title"],
            item["summary"],
            "。".join(item["usableInsights"]),
            "。".join(item["riskNotes"]),
        ]
    )
    texts = chunk_text(extracted_text) or chunk_text(fallback, max_chars=520, overlap=80)
    chunks = []
    for index, text in enumerate(texts, start=1):
        semantic_text = " ".join(
            [
                item["title"],
                text,
                " ".join(item["topics"]),
                " ".join(item["foodMatrix"]),
                " ".join(item["akkMaterial"]),
                item["evidenceLevel"],
            ]
        )
        chunks.append(
            {
                "chunkId": f"{item['knowledgeId']}-chunk-{index:02d}",
                "knowledgeId": item["knowledgeId"],
                "title": item["title"],
                "sourceName": item["sourceName"],
                "sourceFile": item["sourceFile"],
                "sourceUrl": item["sourceUrl"],
                "evidenceLevel": item["evidenceLevel"],
                "evidenceType": item["evidenceType"],
                "topics": item["topics"],
                "foodMatrix": item["foodMatrix"],
                "text": text,
                "embedding": hashed_embedding(semantic_text),
            }
        )
    return chunks


def seed_chunks(seed_item: dict) -> list[dict]:
    text = "。".join(
        [
            seed_item["summary"],
            "。".join(seed_item["usableInsights"]),
            "。".join(seed_item["riskNotes"]),
            "。".join(seed_item["validationMetrics"]),
            seed_item.get("textPreview", ""),
        ]
    )
    chunk = {
        "chunkId": f"{seed_item['knowledgeId']}-chunk-01",
        "knowledgeId": seed_item["knowledgeId"],
        "title": seed_item["title"],
        "sourceName": seed_item["sourceName"],
        "sourceFile": seed_item.get("sourceFile"),
        "sourceUrl": seed_item["sourceUrl"],
        "evidenceLevel": seed_item["evidenceLevel"],
        "evidenceType": seed_item["evidenceType"],
        "topics": seed_item["topics"],
        "foodMatrix": seed_item["foodMatrix"],
        "text": text,
        "embedding": hashed_embedding(f"{seed_item['title']} {text}"),
    }
    return [chunk]


def main() -> None:
    files = []
    for directory in source_dirs():
        files.extend(
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in {".pdf", ".txt", ".md"}
        )

    files = sorted(files, key=lambda item: str(item).lower())
    items = []
    chunks = []
    for index, path in enumerate(files, start=1):
        extracted_text = read_text(path)
        item = build_item(path, index, extracted_text)
        items.append(item)
        chunks.extend(build_chunks(item, extracted_text))

    items.extend(EXTERNAL_SEED_ITEMS)
    for seed_item in EXTERNAL_SEED_ITEMS:
        chunks.extend(seed_chunks(seed_item))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    CHUNK_OUTPUT_PATH.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} knowledge items to {OUTPUT_PATH}")
    print(f"Wrote {len(chunks)} knowledge chunks to {CHUNK_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
