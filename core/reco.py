# -*- coding: utf-8 -*-
"""공고 분석 · 추천 수정안 생성.

이전 버전은 특정 지원자의 문장을 통째로 박아 두었지만,
여기서는 **사용자가 입력한 자기 데이터 + 공고문**만으로 문장을 만들어 냅니다.
그래서 누가 쓰든 자기 이력에 맞는 추천이 나옵니다.
"""

from __future__ import annotations

import re

from . import schema
from .tags import (extract_tags, match_score, coverage, missing_keywords,
                   tag_label, tag_category)


# ---------------------------------------------------------------- 조사 처리
def _has_batchim(word):
    """마지막 글자에 받침이 있는지."""
    for ch in reversed(word or ""):
        if "가" <= ch <= "힣":
            return (ord(ch) - 0xAC00) % 28 != 0
        if ch.isalnum():
            # 영문·숫자는 발음 기준 근사치
            return ch.lower() in "lmnrbktpc0136789"
        # 괄호·기호는 건너뛴다
    return False


def josa(word, with_batchim, without_batchim):
    """받침에 맞는 조사를 붙인다. josa('게임', '을', '를') -> '게임을'"""
    if not word:
        return word
    return word + (with_batchim if _has_batchim(word) else without_batchim)


def eul(w):
    return josa(w, "을", "를")


def gwa(w):
    return josa(w, "과", "와")


def i_ga(w):
    return josa(w, "이", "가")


def euro(w):
    """'로 / 으로' 처리 (받침 없거나 ㄹ 받침이면 '로')."""
    if not w:
        return w
    ch = w[-1]
    if "가" <= ch <= "힣":
        code = (ord(ch) - 0xAC00) % 28
        return w + ("로" if code in (0, 8) else "으로")
    return w + ("으로" if _has_batchim(w) else "로")


def _first_sentence(text):
    if not text:
        return ""
    parts = re.split(r"(?<=다\.)\s+", text.strip())
    return parts[0].strip() if parts else text.strip()


def _strip_period(text):
    return (text or "").strip().rstrip(".").strip()


def _join_sentences(bits):
    """문장 조각들을 마침표로 이어 붙인다."""
    clean = [_strip_period(b) for b in bits if b and b.strip()]
    return ". ".join(clean) + "." if clean else ""


# 여기서 끊으면 자연스러운 자리 (연결어미 > 조사 > 그냥 띄어쓰기)
_BREAK_ENDINGS = ("아", "어", "고", "며", "해", "여", "서", "면", "지만", "하고")
_JOSA_ENDINGS = ("을", "를", "은", "는", "이", "가", "에", "에서", "으로", "로",
                 "와", "과", "부터", "까지", "의", "도")


def _two_lines(text):
    """한 문장을 헤드라인용 두 줄로 나눈다.

    쉼표를 먼저 보고, 없으면 문장이 자연스럽게 끊기는 자리를 찾습니다.
    """
    s = _strip_period(text)
    if len(s) < 16:
        return s + "."
    mid = len(s) / 2.0

    best = None
    for m in re.finditer(r",\s*", s):
        d = abs(m.end() - mid)
        if best is None or d < best[0]:
            best = (d, m.start() + 1, m.end())
    if best is not None:
        _d, cut, resume = best
        return s[:cut].strip() + "\n" + s[resume:].strip() + "."

    for m in re.finditer(r"\s+", s):
        head = s[:m.start()].rstrip()
        word = head.split(" ")[-1] if head else ""
        bonus = 0
        if word.endswith(_BREAK_ENDINGS):
            bonus = len(s) * 0.25
        elif word.endswith(_JOSA_ENDINGS):
            bonus = len(s) * 0.10
        score = abs(m.end() - mid) - bonus
        if best is None or score < best[0]:
            best = (score, m.start(), m.end())
    if best is None:
        return s + "."
    _score, cut, resume = best
    return s[:cut].strip() + "\n" + s[resume:].strip() + "."


def _sort_by_specificity(tags):
    """구체적인 직무 역량이 앞에 오도록 정렬 (공통·소프트스킬은 뒤로)."""
    from .tags import CATEGORY_ORDER

    def key(t):
        cat = tag_category(t)
        return CATEGORY_ORDER.index(cat) if cat in CATEGORY_ORDER else 99
    return sorted(tags, key=key)


# ---------------------------------------------------------------- 분석
def analyze(doc, target):
    jd_text = target.get("jd_text") or ""
    jd_tags = extract_tags(jd_text)
    mine = schema.my_tags(doc)
    score, hit, miss = coverage(mine, jd_tags)
    kws = missing_keywords(jd_text, schema.my_text(doc, target))
    return {
        "jd_tags": jd_tags,
        "my_tags": mine,
        "score": score,
        "hit": hit,
        "miss": miss,
        "missing_keywords": kws,
    }


def rank_projects(doc, jd_tags):
    """공고 적합도 순으로 프로젝트를 정렬한다 (동점이면 원래 순서 유지)."""
    projects = doc["base"]["projects"]
    scored = []
    for i, pr in enumerate(projects):
        overlap = len([t for t in (pr.get("tags") or []) if t in jd_tags])
        scored.append((-overlap, -match_score(pr.get("tags"), jd_tags), i, pr))
    scored.sort(key=lambda x: x[:3])
    return [s[3] for s in scored]


def rank_experience(doc, jd_tags):
    exps = doc["base"]["experience"]
    scored = []
    for i, ex in enumerate(exps):
        overlap = len([t for t in (ex.get("tags") or []) if t in jd_tags])
        scored.append((-overlap, i, ex))
    scored.sort(key=lambda x: x[:2])
    return [s[2] for s in scored]


# ---------------------------------------------------------------- 보완 조언
def gap_advice(doc, tag, jd_tags):
    """미충족 항목마다, 내 데이터 안에서 가장 가까운 근거를 찾아 조언을 만든다."""
    label = tag_label(tag)
    cat = tag_category(tag)
    head = "공고가 요구하는 %s 지금 포트폴리오에서 드러나지 않습니다." % i_ga("'%s'" % label)

    # 소프트스킬은 태그가 아니라 문장으로 증명되는 항목이다
    if cat in ("공통", "경험"):
        return (head + " 이런 항목은 태그가 아니라 문장으로 읽힙니다. "
                "프로젝트 '실행' 항목이나 경력 요약에 그 역량이 드러나는 장면을 "
                "한 줄 넣고, 해당하는 항목의 태그에도 추가해 두세요.")

    # 같은 분류의 태그를 가장 많이 가진 내 항목 = 가장 가까운 근거
    best = None
    for kind, group, name_of in (
            ("프로젝트", doc["base"]["projects"], lambda x: x.get("title") or "무제 프로젝트"),
            ("경력", doc["base"]["experience"],
             lambda x: ("%s %s" % (x.get("org", ""), x.get("role", ""))).strip()),
            ("활동", doc["base"]["activities"], lambda x: x.get("name") or "대외활동")):
        for item in group:
            n = len([t for t in (item.get("tags") or []) if tag_category(t) == cat])
            if n and (best is None or n > best[0]):
                best = (n, kind, name_of(item))

    if best:
        _n, kind, name = best
        return (head + " 가장 가까운 근거는 %s '%s'입니다. 이 항목의 설명에 해당 역량이 "
                "보이도록 문장을 보강하고, 태그에 %s 추가하세요."
                % (kind, _strip_period(name), eul("'%s'" % label)))

    return (head + " 관련 경험이 있다면 프로젝트나 대외활동으로 추가하고, 실무 경험이 없다면 "
            "자유 섹션에 본인의 관점·분석을 직접 작성해 보완하세요. "
            "신입 전형에서는 '직접 써 본 분석'도 유효한 근거가 됩니다.")


# ---------------------------------------------------------------- 추천 생성
def suggest(doc, target):
    """공고와 내 데이터로 추천 수정안을 만든다."""
    res = analyze(doc, target)
    jd_tags = res["jd_tags"]
    b = doc["base"]
    person = b["person"]
    name = person.get("name") or "지원자"
    company = target.get("company") or ""
    position = target.get("position") or person.get("job_title") or "지원 직무"
    position_short = re.sub(r"\s*\(.*?\)\s*", "", position).strip()
    hide = bool(target.get("hide_numbers", True))

    ranked = rank_projects(doc, jd_tags)
    top = ranked[0] if ranked else None
    second = ranked[1] if len(ranked) > 1 else None
    exps = rank_experience(doc, jd_tags)
    exp0 = exps[0] if exps else None

    # 공통·소프트스킬보다 직무 역량이 먼저 오도록 정렬한다
    ranked_hits = _sort_by_specificity(res["hit"]) or _sort_by_specificity(jd_tags)
    top_labels = [tag_label(t) for t in ranked_hits[:3]]

    # ---------- 헤드라인 ----------
    headlines = []
    if top and top.get("subtitle"):
        f = schema.project_fields(top, hide)
        sub = f["subtitle"] or top.get("subtitle")
        headlines.append({
            "label": "경험 중심 · 가장 추천",
            "text": _two_lines(sub),
            "why": "공고 적합도가 가장 높은 '%s'의 결과를 첫 화면에 세웁니다. "
                   "첫 3초에 무엇을 해봤는지 전달되는 구성입니다." % (top.get("title") or ""),
        })
    if len(top_labels) >= 2:
        headlines.append({
            "label": "직무 정합 중심",
            "text": "%s %s\n함께 해온 %s입니다." % (gwa(top_labels[0]), eul(top_labels[1]),
                                                position_short),
            "why": "공고가 요구하는 항목 두 가지를 그대로 받는 문장입니다. 무난하고 안정적입니다.",
        })
    metrics_src = [m for m in (target.get("metrics") or []) if m.get("value")]
    if metrics_src:
        m = metrics_src[0]
        headlines.append({
            "label": "성과 중심",
            "text": "%s %s.\n결과로 증명합니다." % (m.get("label", ""), m.get("value", "")),
            "why": "성과를 전면에 세우는 구성. 경력직 전형이나 지표 중심 직무에 적합합니다.",
        })
    if company:
        headlines.append({
            "label": "지원처 직접 언급",
            "text": "%s가 찾는 %s,\n%s입니다." % (company, position_short, name),
            "why": "지원처를 직접 부르는 방식. 한 회사만 겨냥한 포트폴리오라는 인상을 줍니다.",
        })
    if not headlines:
        headlines.append({
            "label": "기본",
            "text": "%s입니다." % name,
            "why": "내 정보와 공고문을 채우면 더 구체적인 문장을 만들어 드립니다.",
        })

    # ---------- 한 줄 소개 ----------
    taglines = []
    bits = []
    if exp0:
        bits.append("%s %s로 %s" % (exp0.get("org", ""), exp0.get("role", ""),
                                    _strip_period(_first_sentence(exp0.get("summary", "")))))
    if top:
        f = schema.project_fields(top, hide)
        bits.append(_strip_period(_first_sentence(f["result"] or top.get("result", ""))))
    if bits:
        taglines.append({
            "label": "경력 + 성과",
            "text": _join_sentences(bits),
            "why": "경력 한 줄과 대표 성과 한 줄을 이어 붙였습니다. 문장이 길면 뒤를 잘라 쓰세요.",
        })
    if top_labels:
        taglines.append({
            "label": "직무 정합",
            "text": "%s 역량을 %s 직무에 그대로 적용하겠습니다." % (
                ", ".join(top_labels[:3]), position_short),
            "why": "공고 키워드를 그대로 반복해 서류 검토자가 찾는 단어가 보이게 합니다.",
        })

    # ---------- 자기소개 본문 ----------
    paras = []
    if exp0:
        paras.append("%s 직무에 지원하는 %s입니다. %s %s로 %s" % (
            position_short, name, exp0.get("org", ""), exp0.get("role", ""),
            _first_sentence(exp0.get("summary", "")) or "실무를 담당했습니다."))
    else:
        paras.append("%s 직무에 지원하는 %s입니다." % (position_short, name))

    for pr in [p for p in (top, second) if p]:
        f = schema.project_fields(pr, hide)
        acts = pr.get("actions") or []
        lead = _strip_period(acts[0]) if acts else ""
        line = "'%s' 프로젝트에서는 " % (pr.get("title") or "")
        if lead:
            line += "%s 등을 담당했습니다. " % lead
        line += f["result"] or pr.get("result", "")
        paras.append(line.strip())

    extras = []
    for l in b["languages"][:3]:
        if l.get("cert"):
            extras.append("%s(%s)" % (l.get("name", ""), l["cert"]))
        elif l.get("name"):
            extras.append(l["name"])
    certs = [c.get("name", "") for c in b["certificates"][:2] if c.get("name")]
    if extras or certs:
        if extras and certs:
            line = "%s 역량을 갖추고 있으며, %s 자격을 보유하고 있습니다." % (
                " · ".join(extras), " · ".join(certs))
        elif extras:
            line = "%s 역량을 갖추고 있어 해외 시장과 파트너 커뮤니케이션에 활용할 수 있습니다." % " · ".join(extras)
        else:
            line = "%s 자격을 보유하고 있습니다." % " · ".join(certs)
        paras.append(line)

    closing_focus = ", ".join(top_labels[:2]) if top_labels else position_short
    if company:
        paras.append("%s의 %s서 %s 역량을 바탕으로 기여하겠습니다." % (
            company, euro(position_short), closing_focus))
    else:
        paras.append("%s 역량을 바탕으로 기여하겠습니다." % closing_focus)

    intro = {
        "text": "\n\n".join(p for p in paras if p and p.strip()),
        "why": "① 첫 문단에서 지원 직무와 커리어 축을 요약 ② 공고 적합도가 높은 프로젝트 2건을 근거로 배치 "
               "③ 자격 · 어학 ④ 지원처 연결 순서입니다. 서류 검토자가 30초 안에 읽는 구조에 맞췄습니다. "
               "그대로 쓰기보다 초안으로 두고 본인 말투로 다듬으세요.",
    }

    # ---------- 핵심 지표 ----------
    metrics = []
    for pr in ranked[:4]:
        f = schema.project_fields(pr, hide)
        if f["metric_value"] and f["metric_label"]:
            metrics.append({"value": f["metric_value"], "label": f["metric_label"]})
    if len(metrics) < 4:
        if len(b["languages"]) >= 2:
            metrics.append({"value": "%d개 국어" % len(b["languages"]), "label": "구사 언어"})
        if b["awards"]:
            metrics.append({"value": b["awards"][0].get("prize", "수상"), "label": "수상"})
        if b["certificates"]:
            metrics.append({"value": "%d건" % len(b["certificates"]), "label": "보유 자격"})
    metrics = metrics[:4]

    # ---------- 프로젝트 강조 문구 ----------
    emphasis = {}
    for pr in ranked:
        overlap = _sort_by_specificity([t for t in (pr.get("tags") or []) if t in jd_tags])
        if not overlap:
            continue
        joined = ", ".join(tag_label(t) for t in overlap[:3])
        txt = "공고가 요구하는 %s 직접 연결되는 사례입니다." % gwa(joined)
        skills = pr.get("core_skills") or []
        if skills:
            txt += " %s 직접 담당했습니다." % eul(", ".join(skills[:2]))
        emphasis[pr["id"]] = txt

    # ---------- 체크리스트 ----------
    # 구체적인 직무 역량부터, 너무 길어지지 않게 다섯 개까지만
    checklist = [gap_advice(doc, t, jd_tags) for t in _sort_by_specificity(res["miss"])[:5]]
    if not person.get("photo"):
        checklist.append("증명사진이 없습니다. 내 정보 탭에서 사진을 올리면 표지와 프로필 슬라이드가 완성됩니다.")
    if len(b["projects"]) < 3:
        checklist.append("프로젝트가 %d건입니다. 서류 전형에서는 3~5건이 가장 읽기 좋습니다." % len(b["projects"]))
    if not (b["custom"].get("items")):
        checklist.append("자유 섹션이 비어 있습니다. 직무에 대한 본인만의 관점을 한 항목이라도 쓰면 "
                         "면접 질문의 출발점이 됩니다.")
    if res["missing_keywords"]:
        top_kw = ", ".join(w for w, _ in res["missing_keywords"][:5])
        checklist.append("공고에는 자주 나오지만 내 포트폴리오에는 한 번도 안 나오는 단어: %s. "
                         "억지로 넣을 필요는 없지만, 실제 해본 일이라면 그 단어로 바꿔 쓰세요." % top_kw)

    return {
        "analysis": res,
        "headlines": headlines,
        "taglines": taglines,
        "intro": intro,
        "metrics": metrics,
        "project_order": [p["id"] for p in ranked],
        "experience_order": [e["id"] for e in exps],
        "emphasis": emphasis,
        "checklist": checklist,
        "eyebrow": ("for %s · %s" % (company, position_short)) if company else "Portfolio",
    }
