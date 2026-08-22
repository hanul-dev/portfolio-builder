# -*- coding: utf-8 -*-
"""공고문 구조 분석.

지금까지는 공고에서 뽑은 요구사항을 전부 같은 무게로 봤습니다.
하지만 '자격요건'과 '우대사항'은 무게가 다릅니다.
여기서 공고를 구간으로 나눠 **필수 / 담당업무 / 우대**를 구분하고,
포트폴리오에 실제로 들어가야 할 키워드를 뽑습니다.
"""

from __future__ import annotations

import re
from collections import Counter

from .tags import extract_tags, tag_label, _tokens, TAGS

# ---------------------------------------------------------------- 구간 제목
SECTION_WORDS = {
    "duties": ["담당업무", "주요업무", "업무내용", "수행업무", "업무소개", "주요역할",
               "하시게될일", "이런일을하게됩니다", "합류하면", "responsibilities",
               "whatyouwilldo", "aboutthejob", "job"],
    "required": ["자격요건", "지원자격", "필수요건", "필수자격", "필수조건", "지원조건",
                 "이런분을찾습니다", "이런분과함께", "필수", "requirements",
                 "qualifications", "musthave", "basicqualifications"],
    "preferred": ["우대사항", "우대조건", "우대요건", "이런분이면더좋습니다",
                  "이런경험이있다면", "있으면좋아요", "plus", "preferred",
                  "nicetohave", "preferredqualifications", "bonus"],
}

GROUP_LABEL = {"required": "필수", "duties": "담당업무", "preferred": "우대"}
GROUP_WEIGHT = {"required": 2.0, "duties": 1.5, "preferred": 1.0}

_DECOR = "■▶●◆◇★☆【】[]<>〈〉「」《》()（）:：|/-–—=~*#. "


def _norm(line):
    return re.sub(r"\s+", "", (line or "").strip(_DECOR)).lower()


def _section_of(line):
    """이 줄이 구간 제목이면 어느 구간인지."""
    if len(line.strip()) > 30:
        return None
    key = _norm(line)
    if not key or len(key) > 22:
        return None
    for group, words in SECTION_WORDS.items():
        for w in words:
            if key == w or key.startswith(w) or (len(w) >= 4 and w in key):
                return group
    return None


def split_sections(jd_text):
    """공고문을 구간별 텍스트로 나눈다. 제목이 없으면 전부 'other'."""
    out = {"duties": [], "required": [], "preferred": [], "other": []}
    current = "other"
    for raw in (jd_text or "").split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        group = _section_of(line)
        if group:
            current = group
            continue
        out[current].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


# ---------------------------------------------------------------- 근거 찾기
def evidence_for(doc, tag):
    """이 역량을 증명하는 내 항목들."""
    found = []
    b = doc["base"]
    for pr in b["projects"]:
        if tag in (pr.get("tags") or []):
            found.append(("프로젝트", pr.get("title") or "무제"))
    for ex in b["experience"]:
        if tag in (ex.get("tags") or []):
            found.append(("경력", (ex.get("org") or "") + " " + (ex.get("role") or "")))
    for ac in b["activities"]:
        if tag in (ac.get("tags") or []):
            found.append(("활동", ac.get("name") or ""))
    for group, kind in (("skills", "역량"), ("certificates", "자격"), ("awards", "수상")):
        for item in b.get(group) or []:
            if tag in (item.get("tags") or []):
                found.append((kind, item.get("name") or ""))
    for lang in b.get("languages") or []:
        name = lang.get("name", "")
        if tag in ("영어", "일본어", "중국어") and tag[:2] in name:
            found.append(("어학", name))
        elif tag == "외국어" and name:
            found.append(("어학", name))
    return found[:4]


# ---------------------------------------------------------------- 요구사항
def requirements(doc, jd_text, my_tags):
    """구간별 요구 역량과 충족 여부."""
    sections = split_sections(jd_text)
    # 제목을 못 찾으면 전체를 '필수'로 본다 (예전 동작과 같아진다)
    if not any(sections[k] for k in ("duties", "required", "preferred")):
        sections = {"duties": "", "required": jd_text or "", "preferred": "", "other": ""}

    seen = set()
    groups = []
    for key in ("required", "duties", "preferred"):
        tags = []
        for t in extract_tags(sections.get(key, "")):
            if t in seen:
                continue
            seen.add(t)
            tags.append(t)
        if not tags:
            continue
        groups.append({
            "key": key,
            "label": GROUP_LABEL[key],
            "weight": GROUP_WEIGHT[key],
            "tags": tags,
            "hit": [t for t in tags if t in my_tags],
            "miss": [t for t in tags if t not in my_tags],
            "evidence": {t: evidence_for(doc, t) for t in tags if t in my_tags},
        })

    # 구간 밖(other)에만 있는 요구사항도 놓치지 않는다
    rest = [t for t in extract_tags(sections.get("other", "")) if t not in seen]
    if rest:
        groups.append({
            "key": "other", "label": "기타", "weight": 1.0, "tags": rest,
            "hit": [t for t in rest if t in my_tags],
            "miss": [t for t in rest if t not in my_tags],
            "evidence": {t: evidence_for(doc, t) for t in rest if t in my_tags},
        })

    total = sum(g["weight"] * len(g["tags"]) for g in groups)
    got = sum(g["weight"] * len(g["hit"]) for g in groups)
    score = round(got / total * 100) if total else 0
    return {"sections": sections, "groups": groups, "score": score,
            "has_structure": any(sections[k] for k in ("duties", "required", "preferred"))}


# ---------------------------------------------------------------- 키워드
# 공고문에서 자주 보이지만 포트폴리오에 넣을 이유가 없는 말
_SKIP = set("""
지원 자격 요건 사항 우대 담당 업무 내용 모집 채용 전형 제출 서류 면접 합격 근무 조건
회사 조직 부서 신입 경력 이력서 포트폴리오 인재 분야 능력 역량 경험 가능 필수 선호
관련 다양한 각종 기타 이상 이하 등의 등을 등이 대한 대해 위한 위해 통해 통한 그리고
또는 있는 있습니다 합니다 하는 하며 하고 경우 여러 하나 정도 이런 그런 어떤 매우 항상
직무 포지션 팀원 구성원 우리 저희 함께 모든 다음 아래 시 및 또한 물론 특히
""".split())


# 흔한 조사 — 긴 것부터 떼어낸다
_JOSA = ("으로서", "으로써", "에서의", "에게서", "이라는", "으로", "에서", "에게", "한테",
         "까지", "부터", "이나", "처럼", "보다", "와의", "과의", "들의", "라는",
         "의", "을", "를", "이", "가", "은", "는", "에", "도", "만", "와", "과", "로")

# 서술어로 끝나는 토막은 키워드가 아니다
_VERBISH = re.compile(r"(하는|하며|하고|하여|하신|해서|으신|이신|있는|있으신|같은|되는|"
                      r"되며|되어|되고|합니다|입니다|드립니다|나신|으로서)$")
# 짧은데 연결어미로 끝나면 거의 동사·형용사 토막이다 ('강하고', '높으며')
_SHORT_VERBISH = re.compile(r"[가-힣]{1,3}(고|며|서|야|지|면)$")

_ALNUM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/+.#&-]*$")


def _stem(word):
    """조사를 떼어 낸 형태. 영문·기호는 그대로 둔다."""
    if _ALNUM.match(word):
        return word
    for j in _JOSA:
        if word.endswith(j) and len(word) - len(j) >= 2:
            return word[:-len(j)]
    return word


def keyword_plan(doc, jd_text, my_text, limit=20, my_tags=None):
    """포트폴리오에 들어가야 할 키워드와, 지금 쓰고 있는지.

    사전에 잡힌 것은 '역량', 그 밖의 말은 그 회사가 쓰는 '용어' 로 봅니다.
    조사가 붙은 토막('높으신', '맡은')이 섞이지 않도록 걸러 냅니다.
    """
    sections = split_sections(jd_text)
    if not any(sections[k] for k in ("duties", "required", "preferred")):
        sections = {"duties": "", "required": jd_text or "", "preferred": "", "other": ""}

    mine = (my_text or "").lower()
    my_tags = my_tags or []
    scored = {}

    # 1) 사전에 잡힌 역량 — 충족 여부는 태그로 판단해야 정확하다
    for key in ("required", "duties", "preferred", "other"):
        text = sections.get(key, "")
        if not text:
            continue
        weight = GROUP_WEIGHT.get(key, 1.0)
        for tag in extract_tags(text):
            label = tag_label(tag)
            cur = scored.get(label)
            if cur and cur["weight"] >= weight:
                continue
            words = TAGS[tag][2] if tag in TAGS else [label]
            scored[label] = {
                "word": words[0], "label": label, "kind": "역량",
                "group": GROUP_LABEL.get(key, "기타"), "weight": weight,
                "count": max(text.count(w) for w in words) or 1,
                # 요구사항 카드와 같은 기준으로 판단해야 앞뒤가 맞는다.
                # 단어가 글에 있어도 역량으로 안 잡혔으면 '안 씀' 이다.
                "used": tag in my_tags,
                "tag": tag,
            }

    # 2) 사전에 없는 말 — 두 번 이상 나온 것만. 한 번뿐인 말은 대개 조사 붙은 토막이다
    counts = Counter()
    for key in ("required", "duties", "preferred"):
        text = sections.get(key, "")
        if not text:
            continue
        weight = GROUP_WEIGHT.get(key, 1.0)
        for raw in _tokens(text):
            word = _stem(raw)
            if len(word) < 2 or word in _SKIP or _VERBISH.search(word):
                continue
            if _SHORT_VERBISH.match(word):
                continue
            counts[word] += 1
            key_of = scored.get(word)
            if key_of:
                continue
            scored.setdefault("__" + word, {
                "word": word, "label": word, "kind": "용어",
                "group": GROUP_LABEL.get(key, "기타"), "weight": weight,
                "count": 0, "used": word.lower() in mine, "tag": None,
            })

    items = []
    for key, item in scored.items():
        if item["kind"] == "용어":
            word = item["word"]
            item["count"] = counts.get(word, 0)
            # 두 번 이상 나오면 확실하고, 한 번뿐이어도
            # 영문 약어(SAP·WMS·SQL)나 긴 전문어(콜드체인·선입선출)는 핵심일 때가 많다.
            solid = item["count"] >= 2 or _ALNUM.match(word) or len(word) >= 3
            if not solid:
                continue
            if any(item["word"] in o["label"] for o in scored.values()
                   if o["kind"] == "역량"):             # 역량과 겹치면 중복
                continue
        items.append(item)

    # 역량 먼저, 그다음 가중치 · 미사용 · 빈도 순
    items.sort(key=lambda x: (x["kind"] != "역량", -x["weight"], x["used"],
                              -x["count"], x["label"]))
    return items[:limit]
