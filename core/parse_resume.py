# -*- coding: utf-8 -*-
"""이력서 글자 -> 이력 항목 (규칙 기반).

LLM 없이 동작합니다. 대신 완벽하지 않으므로,
결과는 반드시 사용자가 확인·수정하는 화면을 거쳐야 합니다.
못 읽은 줄은 버리지 않고 report 에 담아 돌려줍니다.

두 가지 경로로 읽습니다.
  1) 채용 사이트 이력서 양식 — '기간 (재직기간) 고용형태 직무' 와
     '[프로젝트명]' 같은 라벨 문법을 그대로 해석합니다. 정확도가 높습니다.
  2) 자유 형식 — 섹션 제목과 날짜 패턴만으로 어림잡아 나눕니다.
1번으로 아무것도 못 건지면 2번으로 넘어갑니다.
"""

from __future__ import annotations

import re

from . import schema
from .extract import clean_text
from .tags import extract_tags

# ---------------------------------------------------------------- 패턴
YEAR = r"(?:19|20)\d{2}"
DATE = r"%s\s*(?:[.\-/년]\s*\d{1,2}\s*(?:[.\-/월]\s*\d{0,2}\s*일?)?)?" % YEAR
NOW = r"(?:재\s*직\s*중|재직|현재|now|present)"
RANGE = re.compile(r"(%s)\s*[~\-–—]\s*(%s|%s)" % (DATE, DATE, NOW), re.I)
RANGE_AT_START = re.compile(r"^\s*(%s)\s*[~\-–—]\s*(%s|%s)" % (DATE, DATE, NOW), re.I)
ANY_DATE = re.compile(DATE)
YM = re.compile(r"^\s*(%s\s*[.\-/년]\s*\d{1,2})\s*[월]?\s*$" % YEAR)

# '(6개월)', '(1년 8개월)' — 재직 기간 표시. 프로젝트 줄과 구분하는 핵심 신호.
DURATION = re.compile(r"[(（]\s*(?:\d+\s*년\s*)?(?:\d+\s*개월)?\s*[)）]")
EMPLOY = re.compile(r"(정규직|계약직|인턴|프리랜서|파견직|파견|아르바이트|위촉직|기타직)")

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"01[016-9][-.\s]?\d{3,4}[-.\s]?\d{4}")
BIRTH_LABELED = re.compile(r"(?:생년월일|생일|생년)\s*[:：]?\s*"
                           r"((?:19|20)\d{2}\s*[.\-/년]\s*\d{1,2}\s*[.\-/월]\s*\d{1,2})")
BIRTH_PLAIN = re.compile(r"\b((?:19|20)\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})\b")

BULLET = re.compile(r"^\s*(?:[-–—*·•▪◦○●■□▶►]|\d+[.)])\s+")
LABEL = re.compile(r"^\s*[\[【]\s*([^\]】]+?)\s*[\]】]\s*$")
KIND = re.compile(r"^(.*?)[(（]\s*([^)）]{2,12})\s*[)）]\s*$")

DECOR = "■▶●◆◇★☆【】[]<>〈〉「」《》:：|/ㅇ-–—=~*#"
SCHOOL = re.compile(r"(대학교|대학원|대학|고등학교|고교|전문대|캠퍼스|아카데미)")

# ---------------------------------------------------------------- 섹션 제목
SECTIONS = {
    "profile": ["인적사항", "기본정보", "개인정보", "프로필", "인적정보", "profile"],
    "education": ["학력", "학력사항", "학업", "education"],
    "experience": ["경력", "경력사항", "경력기술", "경력기술서", "업무경험", "근무경력",
                   "직장경력", "career", "experience", "workexperience"],
    "projects": ["프로젝트", "주요프로젝트", "프로젝트경험", "수행프로젝트", "프로젝트이력",
                 "포트폴리오", "project", "projects"],
    "certificates": ["자격", "자격증", "자격사항", "보유자격", "면허", "자격면허",
                     "certificate", "certificates", "license"],
    "awards": ["수상", "수상내역", "수상경력", "수상실적", "award", "awards", "honors"],
    "languages": ["어학", "어학능력", "어학사항", "외국어", "언어", "language", "languages"],
    "activities": ["활동", "대외활동", "교내활동", "봉사활동", "사회활동", "동아리", "기타",
                   "activity", "activities"],
    "skills": ["기술", "스킬", "보유기술", "보유역량", "사용툴", "툴", "기술스택",
               "skill", "skills", "tech", "tools"],
    "intro": ["자기소개", "자기소개서", "소개", "introduction", "aboutme"],
}

# '이름(구분)' 의 구분을 어느 항목으로 보낼지
KIND_MAP = {
    "자격증": "certificates", "면허": "certificates", "자격": "certificates",
    "수상경력": "awards", "수상": "awards",
    "대외활동": "activities", "교내활동": "activities", "자원봉사": "activities",
    "봉사활동": "activities", "동아리": "activities", "인턴": "activities",
    "외국거주경험": "activities", "외국거주 경험": "activities", "교육": "activities",
    "어학시험": "languages", "어학": "languages",
}

# 프로젝트 라벨 문법
LABEL_MAP = {
    "프로젝트명": "title", "프로젝트": "title", "과제명": "title", "제목": "title",
    "기간": "period", "수행기간": "period", "프로젝트기간": "period", "진행기간": "period",
    "프로젝트배경": "background", "배경": "background", "개요": "background",
    "프로젝트개요": "background", "상황": "background",
    "담당역할및실행": "actions", "담당역할": "actions", "담당업무": "actions",
    "주요업무": "actions", "역할": "actions", "실행": "actions", "수행업무": "actions",
    "핵심역량": "core_skills", "사용스킬": "core_skills", "보유역량": "core_skills",
    "사용기술": "core_skills", "기술스택": "core_skills",
    "성과": "result", "결과": "result", "프로젝트성과": "result", "기여도": "result",
}

LANG_NAMES = ["영어", "일본어", "중국어", "독일어", "프랑스어", "스페인어", "러시아어", "베트남어"]
LANG_TESTS = re.compile(
    r"(TOEIC|TOEFL|OPIc|OPIC|TEPS|IELTS|JLPT|JPT|HSK|DELE|DELF|TOPIK)"
    r"(?:\s*(N\s?[1-5]|[1-6]\s?급|\d{2,4}\s?점?|[A-C][12]|I[HLM]\d?|A[LM]))?", re.I)

# 띄어쓰기가 들어간 툴 이름 — 스킬을 쪼갤 때 붙여 둡니다
MULTIWORD_TOOLS = [
    "Google Analytics", "Google Ads", "Adobe Photoshop", "Adobe Illustrator",
    "Adobe Premiere", "After Effects", "Premiere Pro", "Power BI", "Microsoft 365",
    "Microsoft Office", "MS Office", "Google Sheets", "Google Docs", "Final Cut",
    "Visual Studio", "Android Studio", "Amazon Web Services", "Naver Works",
]

PRIZE = re.compile(r"(대상|최우수상|우수상|장려상|금상|은상|동상|입선|특선|"
                   r"\d+\s*등|\d+\s*위|grand\s*prize|1st|2nd|3rd)", re.I)


# ---------------------------------------------------------------- 도우미
def _norm(line):
    return re.sub(r"\s+", "", (line or "").strip(DECOR + " ")).lower()


# '1. 경력사항', '3) 학력', 'Ⅱ. 자격' 처럼 번호를 매긴 제목.
# 한글 이력서 양식에서 아주 흔한데, 번호가 붙으면 제목으로 못 알아본다.
NUMBERED_HEAD = re.compile(r"^[(（]?(?:\d{1,2}|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]{1,4}|[IVX]{1,4})"
                           r"[.)．）]\s*|^[①-⑳➀-➉]\s*")


def _section_of(line):
    """섹션 제목이면 종류를 돌려준다. 여러 종류가 섞인 제목이면 'mixed'."""
    if len(line.strip()) > 26:
        return None
    key = _norm(NUMBERED_HEAD.sub("", line.strip(DECOR + " ")))
    key = re.sub(r"[(（].*$", "", key)
    key = re.sub(r"(총)?\d+\s*(년|개월|건|개|년차).*$", "", key)
    if not key:
        return None

    parts = [p for p in re.split(r"[/·ㆍ,&]|및", key) if p]
    hits = []
    for part in parts:
        for name, words in SECTIONS.items():
            if part in words and name not in hits:
                hits.append(name)
    if not hits and len(key) <= 14:
        for name, words in SECTIONS.items():
            for w in words:
                if len(w) >= 2 and key.startswith(w) and len(key) - len(w) <= 6:
                    if name not in hits:
                        hits.append(name)
                    break
    if not hits:
        return None
    return hits[0] if len(hits) == 1 else "mixed"


def _strip_bullet(line):
    return BULLET.sub("", line or "").strip()


def _period_of(line):
    m = RANGE.search(line or "")
    if m:
        period = re.sub(r"\s+", " ", m.group(0)).strip()
        rest = (line[:m.start()] + " " + line[m.end():]).strip(DECOR + " ")
        return period, re.sub(r"\s{2,}", " ", rest).strip()
    return "", (line or "").strip()


def _split_title(rest):
    rest = rest.strip(DECOR + " ")
    for sep in ["|", "／", "/", " - ", "·", "ㆍ", ",", "  "]:
        if sep in rest:
            parts = [p.strip(DECOR + " ") for p in rest.split(sep) if p.strip(DECOR + " ")]
            if len(parts) >= 2:
                return parts[0], " ".join(parts[1:])
    return rest, ""


def _label_of(line):
    m = LABEL.match(line or "")
    if not m:
        return None
    return LABEL_MAP.get(re.sub(r"\s+", "", m.group(1)))


# '[프로젝트명] 브랜드 캠페인' 처럼 라벨과 값이 한 줄에 붙어 있는 형태.
# 라벨만 있는 줄로 쓰는 이력서도 있고 이렇게 쓰는 이력서도 있어서, 여기서
# 두 줄로 펴 놓고 뒤쪽 규칙은 하나만 알게 합니다.
INLINE_LABEL = re.compile(r"^[ \t]*[\[【]\s*([^\]】\n]{1,24}?)\s*[\]】][ \t]*(\S.*)$")


def split_inline_labels(text):
    out = []
    for line in (text or "").split("\n"):
        m = INLINE_LABEL.match(line)
        if m and re.sub(r"\s+", "", m.group(1)) in LABEL_MAP:
            out.append("[%s]" % m.group(1).strip())
            out.append(m.group(2).strip())
        else:
            out.append(line)
    return "\n".join(out)


def split_sections(text):
    out = {"head": []}
    current = "head"
    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        if not LABEL.match(line):              # '[프로젝트명]' 은 제목이 아니다
            name = _section_of(line)
            if name:
                current = name
                out.setdefault(current, [])
                continue
        out.setdefault(current, []).append(line)
    return out


# ---------------------------------------------------------------- 경력 · 프로젝트
NUMBER = re.compile(r"([+\-]?\d+(?:\.\d+)?\s*(?:%|퍼센트|배|건|명|만|억|원|점|위|등))")


def metric_from(text):
    """'CPI 30% 이상 개선' 같은 성과 문장에서 대표 숫자와 이름을 뽑는다."""
    if not text:
        return "", ""
    m = NUMBER.search(text)
    if not m:
        return "", ""
    value = re.sub(r"\s+", "", m.group(1))
    before = text[:m.start()].strip(DECOR + " ,")
    label = before.split()[-1] if before.split() else ""
    label = label.strip(DECOR + " ,")
    if len(label) > 14:
        label = label[:14]
    return value, label


def _flush_project(cur, company, out):
    if not cur:
        return
    title = cur["title"] or cur["role"] or "프로젝트"
    if not (cur["actions"] or cur["background"] or cur["result"]):
        return
    value, label = metric_from(cur["result"])
    pr = schema.empty_project()
    pr.update({
        "title": title[:80],
        "org": company or "",
        "period": cur["period"],
        "my_role": cur["role"],
        "background": cur["background"].strip(),
        "actions": cur["actions"][:8],
        "result": cur["result"].strip(),
        "core_skills": cur["core_skills"][:5],
        "metric_value": value,
        "metric_label": label,
    })
    pr["tags"] = extract_tags(" ".join(
        [title, cur["background"], cur["result"]] + cur["actions"] + cur["core_skills"]))
    out.append(pr)


def _tenure_match(line):
    """'2024.09 - 재직중 (1년 8개월) 정규직 매니저' 인지 판별."""
    m = RANGE_AT_START.match(line)
    if not m:
        return None
    return m if DURATION.search(line[m.end():]) else None


def _parse_career(lines):
    """채용 사이트 양식: 회사 → 재직 줄 → 성과 → 프로젝트 블록."""
    lines = [l.strip() for l in lines if l.strip()]

    # 1차: 재직 줄 바로 앞줄이 회사명이다. 먼저 표시해 둬야
    # 프로젝트 본문 한가운데 있는 회사명을 놓치지 않는다.
    tenure = [bool(_tenure_match(l)) for l in lines]
    company_at, skip = {}, set()
    for i, is_tenure in enumerate(tenure):
        if not (is_tenure and i > 0):
            continue
        prev = lines[i - 1]
        if tenure[i - 1] or LABEL.match(prev) or BULLET.match(prev) \
                or RANGE_AT_START.match(prev) or len(prev) > 40:
            continue
        company_at[i] = prev.strip(DECOR + " ")
        skip.add(i - 1)

    exps, projects = [], []
    company = ""
    cur_exp = None
    cur_proj = None
    field = None          # 지금 어떤 라벨 아래에 있는지
    pending_line = ""     # 프로젝트 기간 줄 바로 앞의 한 줄 = 그 프로젝트의 성과

    for idx, line in enumerate(lines):
        if idx in skip:                       # 회사명 줄은 이미 썼다
            continue

        label = _label_of(line)
        if label:
            field = label
            if field == "title":
                # [프로젝트명] 이 또 나오면 그 앞은 끝난 프로젝트다.
                # 안 끊으면 여러 건이 한 건으로 뭉쳐 버린다.
                if cur_proj is not None and cur_proj["title"]:
                    _flush_project(cur_proj, company, projects)
                    cur_proj = None
                if cur_proj is None:
                    cur_proj = {"title": "", "period": "", "role": "", "background": "",
                                "actions": [], "core_skills": [], "result": ""}
            continue

        # '[기간]' 바로 다음 줄은 그 프로젝트의 날짜다. 이걸 아래에서
        # '새 프로젝트가 시작되는 줄' 로 보면, 방금 읽은 제목이 통째로 날아간다.
        if field == "period" and cur_proj is not None and RANGE.search(line):
            got, rest = _period_of(line)
            cur_proj["period"] = got or line.strip(DECOR + " ")
            if rest and not cur_proj["title"]:
                cur_proj["title"] = rest
            field = None
            continue

        m = RANGE_AT_START.match(line)
        if m:
            rest = line[m.end():].strip(DECOR + " ")
            period = re.sub(r"\s+", " ", m.group(0)).strip()
            dur = DURATION.search(rest)

            if dur:                                   # 재직 줄 -> 새 회사 경력
                _flush_project(cur_proj, company, projects)
                cur_proj, field = None, None
                rest = (rest[:dur.start()] + " " + rest[dur.end():]).strip(DECOR + " ")
                emp = EMPLOY.search(rest)
                etype = emp.group(0) if emp else ""
                if emp:
                    rest = (rest[:emp.start()] + " " + rest[emp.end():]).strip(DECOR + " ")
                company = company_at.get(idx, company)
                cur_exp = schema.empty_experience()
                cur_exp.update({
                    "org": company, "role": rest.strip(), "type": etype,
                    "period": period,
                    "duration": re.sub(r"[()（）]", "", dur.group(0)).strip(),
                })
                exps.append(cur_exp)
                pending_line = ""
            else:                                     # 프로젝트 줄
                _flush_project(cur_proj, company, projects)
                cur_proj = {"title": "", "period": period, "role": rest.strip(),
                            "background": "", "actions": [], "core_skills": [],
                            "result": pending_line}
                pending_line = ""
                field = None
            continue

        # 라벨 안쪽 내용
        if cur_proj is not None and field:
            body = _strip_bullet(line)
            is_bullet = bool(BULLET.match(line))
            # 목록형 라벨은 불릿까지만. 불릿 없는 줄이 나오면 목록이 끝난 것으로 본다
            # (그 줄은 대개 다음 프로젝트의 성과 한 줄이다).
            # '지금 채우는 칸' 이 이미 찼는지만 본다. 둘을 같이 보면 [핵심 역량] 이
            # [담당 역할] 뒤에 올 때 첫 줄부터 버려진다.
            own = cur_proj["actions"] if field == "actions" else \
                cur_proj["core_skills"] if field == "core_skills" else None
            if own is not None and not is_bullet and own:
                field = None
            elif not body:
                continue
            elif field == "title":
                cur_proj["title"] = (cur_proj["title"] + " " + body).strip()
                continue
            elif field == "actions":
                if is_bullet or not cur_proj["actions"]:
                    cur_proj["actions"].append(body)
                else:
                    cur_proj["actions"][-1] += " " + body
                continue
            elif field == "core_skills":
                # 역량은 '기획, 분석 · 운영' 처럼 한 줄에 몰아 적는 경우가 많다
                for part in re.split(r"[,،/·ㆍ|]", body):
                    part = part.strip(DECOR + " ")
                    if part:
                        cur_proj["core_skills"].append(part)
                continue
            else:
                cur_proj[field] = (cur_proj[field] + " " + body).strip()
                continue

        # 라벨 밖: 재직 줄 바로 다음 한 줄은 그 경력의 성과 요약
        if cur_exp is not None and not cur_exp["summary"] and cur_proj is None:
            cur_exp["summary"] = line.strip(DECOR + " ")
        else:
            # 다음 프로젝트의 성과 줄일 수 있으니 들고 있는다
            pending_line = line.strip(DECOR + " ")

    _flush_project(cur_proj, company, projects)

    for ex in exps:
        ex["tags"] = extract_tags(" ".join([ex["org"], ex["role"], ex["summary"]]))
    return exps, projects


def _parse_experience_loose(lines):
    """자유 형식용 대충 나누기."""
    out, cur = [], None
    for line in lines:
        if RANGE.search(line):
            if cur:
                out.append(cur)
            cur = {"head": line, "body": []}
        elif cur:
            cur["body"].append(line)
    if cur:
        out.append(cur)

    exps = []
    for e in out[:12]:
        period, rest = _period_of(e["head"])
        org, role = _split_title(rest)
        bullets = [_strip_bullet(x) for x in e["body"] if BULLET.match(x)]
        prose = [x.strip() for x in e["body"] if not BULLET.match(x)]
        if not org and prose:
            org = prose.pop(0)
        if not (org or role or bullets):
            continue
        item = schema.empty_experience()
        item.update({"org": org, "role": role, "period": period,
                     "summary": " ".join(prose).strip(), "points": bullets[:6]})
        item["tags"] = extract_tags(" ".join([org, role, item["summary"]] + bullets))
        exps.append(item)
    return exps


def _parse_projects_loose(lines):
    out, cur = [], None

    def flush():
        if cur and (cur["title"] or cur["actions"]):
            pr = schema.empty_project()
            pr.update(cur)
            pr["tags"] = extract_tags(" ".join([cur["title"], cur["background"]] + cur["actions"]))
            out.append(pr)

    for line in lines:
        label = _label_of(line)
        if label:
            continue
        is_bullet = bool(BULLET.match(line))
        period, rest = _period_of(line)
        if not is_bullet and rest and len(rest) < 60:
            flush()
            cur = {"title": rest, "period": period, "background": "", "actions": [],
                   "org": "", "my_role": "", "core_skills": [], "result": ""}
        elif cur is None:
            cur = {"title": _strip_bullet(line)[:60], "period": "", "background": "",
                   "actions": [], "org": "", "my_role": "", "core_skills": [], "result": ""}
        elif is_bullet:
            cur["actions"].append(_strip_bullet(line))
        else:
            cur["background"] = (cur["background"] + " " + line.strip()).strip()
    flush()
    return out[:10]


# ---------------------------------------------------------------- 나머지 섹션
def _parse_education(lines):
    out, pending = [], ""
    for raw in lines[:20]:
        line = raw.strip(DECOR + " ")
        if not line:
            continue
        if re.match(r"^(성적|학점|평점|GPA)", line, re.I):
            if out:
                out[-1]["note"] = (out[-1]["note"] + " " + line).strip()
            continue
        period, rest = _period_of(line)
        if not period:
            pending = line                       # 학교명만 있는 줄
            continue
        school = pending
        dept = rest
        if not school:
            m = SCHOOL.search(rest)
            if m:
                school, dept = rest[:m.end()].strip(), rest[m.end():].strip()
            else:
                school, dept = _split_title(rest)
        note = ""
        m = re.search(r"(졸업예정|졸업|재학|수료|휴학|중퇴|편입)", dept)
        if m:
            note = m.group(0)
            dept = (dept[:m.start()] + " " + dept[m.end():]).strip(DECOR + " ")
        if school:
            out.append({"school": school, "dept": dept, "period": period, "note": note})
        pending = ""
    return out


def _parse_languages(lines):
    merged = {}
    for raw in lines[:14]:
        line = _strip_bullet(raw)
        name = next((n for n in LANG_NAMES if n in line), "")
        m = LANG_TESTS.search(line)
        cert = re.sub(r"\s+", " ", m.group(0)).strip() if m else ""
        if not name and m:
            name = {"JLPT": "일본어", "JPT": "일본어", "HSK": "중국어",
                    "TOPIK": "한국어"}.get(m.group(1).upper(), "영어")
        if not name:
            continue
        level = ""
        for key in ["원어민", "유창", "비즈니스", "일상회화", "업무가능", "중급", "초급"]:
            if key in line:
                level = key
                break
        cur = merged.setdefault(name, {"name": name, "level": "", "cert": "",
                                       "date": "", "bar": 80})
        cur["cert"] = cur["cert"] or cert
        cur["level"] = cur["level"] or level
    return list(merged.values())


def _parse_skills(lines):
    tokens = []
    for raw in lines[:14]:
        line = _strip_bullet(raw)
        line = re.sub(r"^[^:：]{0,12}[:：]\s*", "", line)
        holder = {}
        for i, tool in enumerate(MULTIWORD_TOOLS):      # 띄어쓴 툴 이름 보호
            if tool.lower() in line.lower():
                key = "\x00%d\x00" % i
                line = re.sub(re.escape(tool), key, line, flags=re.I)
                holder[key] = tool
        for tok in re.split(r"[,/·ㆍ|]|\s+", line):
            tok = holder.get(tok, tok).strip(DECOR + " ")
            if 1 < len(tok) <= 40:
                tokens.append(tok)
    seen, out = set(), []
    for tok in tokens:
        if tok.lower() in seen:
            continue
        seen.add(tok.lower())
        out.append({"name": tok, "bar": 80, "tags": extract_tags(tok)})
    return out[:14]


def _parse_mixed(lines):
    """'수상/자격증/기타' 처럼 섞인 구간. '이름(구분)' 의 구분으로 갈라 담는다."""
    buckets = {"certificates": [], "awards": [], "activities": [], "languages": []}
    cur, kind = None, None

    def flush():
        if not cur or not kind:
            return
        name = cur["name"]
        date = cur["date"]
        detail = [d for d in cur["detail"] if d]
        if kind == "certificates":
            org = ""
            for d in detail:
                m = re.search(r"(?:발급기관|발행처|주관)\s*[-:：]?\s*(.+)", d)
                if m:
                    org = m.group(1).strip()
            buckets["certificates"].append(
                {"name": name, "org": org, "date": date, "tags": extract_tags(name)})
        elif kind == "awards":
            prize = ""
            for d in detail:
                m = PRIZE.search(d)
                if m:
                    prize = m.group(0)
                    break
            buckets["awards"].append({"name": name, "prize": prize, "date": date,
                                      "tags": extract_tags(name) + ["공모전"]})
        else:
            period = date
            desc = []
            for d in detail:
                if RANGE.search(d) and len(d) < 30:
                    period = re.sub(r"\s+", " ", RANGE.search(d).group(0))
                else:
                    desc.append(_strip_bullet(d))
            text = " ".join(desc).strip()
            label = name if len(name) > 3 else ("%s (%s)" % (name, cur["kind"]))
            buckets["activities"].append({"name": label, "period": period, "type": cur["kind"],
                                          "desc": text, "tags": extract_tags(name + " " + text)})

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        m = KIND.match(line)
        if m and not BULLET.match(line):
            flush()
            label = re.sub(r"\s+", "", m.group(2))
            kind = KIND_MAP.get(label, "activities")
            cur = {"name": m.group(1).strip(DECOR + " "), "kind": m.group(2).strip(),
                   "date": "", "detail": []}
            continue
        if cur is None:
            continue
        ym = YM.match(line)
        if ym and not cur["date"]:
            cur["date"] = re.sub(r"\s+", "", ym.group(1))
            continue
        m2 = re.match(r"^\s*(%s\s*[.\-/년]\s*\d{1,2})\s+\S+" % YEAR, line)
        if m2 and not cur["date"]:
            cur["date"] = re.sub(r"\s+", "", m2.group(1))
            continue
        cur["detail"].append(line)
    flush()
    return buckets


def _parse_certificates_simple(lines):
    out = []
    for raw in lines[:15]:
        line = _strip_bullet(raw)
        period, rest = _period_of(line)
        if not period:
            m = ANY_DATE.search(line)
            if m:
                period = m.group(0).strip()
                rest = (line[:m.start()] + " " + line[m.end():]).strip(DECOR + " ")
        if not rest:
            continue
        name, org = rest, ""
        m = re.search(r"[（(]([^）)]+)[）)]", rest)
        if m:
            name, org = rest[:m.start()].strip(DECOR + " "), m.group(1).strip()
        else:
            name, org = _split_title(rest)
        if name:
            out.append({"name": name, "org": org, "date": period, "tags": extract_tags(name)})
    return out


def _parse_awards_simple(lines):
    out = []
    for raw in lines[:15]:
        line = _strip_bullet(raw)
        period, rest = _period_of(line)
        if not period:
            m = ANY_DATE.search(line)
            if m:
                period = m.group(0).strip()
                rest = (line[:m.start()] + " " + line[m.end():]).strip(DECOR + " ")
        if not rest:
            continue
        prize = ""
        m = PRIZE.search(rest)
        if m:
            prize = m.group(0)
            rest = (rest[:m.start()] + " " + rest[m.end():]).strip(DECOR + " ")
        if rest:
            out.append({"name": rest, "prize": prize, "date": period,
                        "tags": extract_tags(rest) + ["공모전"]})
    return out


def _parse_activities_simple(lines):
    out, cur = [], None
    for raw in lines[:30]:
        line = raw.strip()
        if not line:
            continue
        period, rest = _period_of(line)
        if period and rest and not BULLET.match(line):
            if cur:
                out.append(cur)
            cur = {"name": rest, "period": period, "type": "", "desc": "", "tags": []}
        elif cur:
            cur["desc"] = (cur["desc"] + " " + _strip_bullet(line)).strip()
        else:
            cur = {"name": line.strip(DECOR + " "), "period": "", "type": "",
                   "desc": "", "tags": []}
    if cur:
        out.append(cur)
    for a in out:
        a["tags"] = extract_tags(a["name"] + " " + a["desc"])
    return out[:10]


# ---------------------------------------------------------------- 인적사항
def _parse_person(text, head_lines):
    person = schema.empty_person()

    m = EMAIL.search(text)
    if m:
        person["email"] = m.group(0)
    m = PHONE.search(text)
    if m:
        person["phone"] = m.group(0)

    m = re.search(r"(?:이\s*름|성\s*명|name)\s*[:：]?\s*([가-힣]{2,5}|[A-Za-z][A-Za-z ]{2,29})",
                  text, re.I)
    if m:
        person["name"] = m.group(1).strip()
    else:
        for line in head_lines[:6]:
            cand = line.strip(DECOR + " ")
            if re.fullmatch(r"[가-힣]{2,4}", cand):
                person["name"] = cand
                break

    m = BIRTH_LABELED.search(text)
    if m:
        person["birth"] = re.sub(r"\s+", "", m.group(1))
    else:
        for m in BIRTH_PLAIN.finditer(text):
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1950 <= y <= 2015 and 1 <= mo <= 12 and 1 <= d <= 31:
                start, end = m.start(), m.end()
                if re.search(r"[~\-–—]\s*$", text[max(0, start - 3):start]):
                    continue                     # 기간의 뒷부분이면 건너뛴다
                if re.match(r"^\s*[~\-–—]", text[end:end + 3]):
                    continue                     # 기간의 앞부분이면 건너뛴다
                person["birth"] = "%04d.%02d.%02d" % (y, mo, d)
                break

    m = re.search(r"(?:주\s*소|거\s*주\s*지|주소지)\s*[:：]?\s*([^\n]{2,40})", text)
    if m:
        person["location"] = m.group(1).strip(DECOR + " ")

    for m in re.finditer(r"https?://[^\s,)]+", text):
        url = m.group(0).rstrip(".")
        label = "링크"
        for key, name in [("github", "GitHub"), ("notion", "Notion"), ("linkedin", "LinkedIn"),
                          ("velog", "Velog"), ("tistory", "블로그"), ("brunch", "브런치"),
                          ("blog", "블로그"), ("behance", "Behance")]:
            if key in url.lower():
                label = name
                break
        if not any(l["url"] == url for l in person["links"]):
            person["links"].append({"label": label, "url": url})
        if len(person["links"]) >= 4:
            break
    return person


# ---------------------------------------------------------------- 진입점
def parse(text):
    """이력서 글자 -> (doc, report)"""
    text = split_inline_labels(clean_text(text))
    doc = schema.empty_doc()
    base = doc["base"]

    sections = split_sections(text)
    head = sections.get("head", [])
    base["person"] = _parse_person(text, head + sections.get("profile", []))

    # --- 경력 · 프로젝트
    career_lines = sections.get("experience", [])
    exps, projs = _parse_career(career_lines) if career_lines else ([], [])
    if not exps and career_lines:
        exps = _parse_experience_loose(career_lines)
    base["experience"] = exps

    proj_lines = sections.get("projects", [])
    if proj_lines:
        _, labeled = _parse_career(proj_lines)
        projs = projs + (labeled or _parse_projects_loose(proj_lines))
    base["projects"] = projs[:10]

    # --- 나머지
    base["education"] = _parse_education(sections.get("education", []))
    base["languages"] = _parse_languages(sections.get("languages", []))
    base["skills"] = _parse_skills(sections.get("skills", []))
    base["certificates"] = _parse_certificates_simple(sections.get("certificates", []))
    base["awards"] = _parse_awards_simple(sections.get("awards", []))
    base["activities"] = _parse_activities_simple(sections.get("activities", []))

    if sections.get("mixed"):
        got = _parse_mixed(sections["mixed"])
        base["certificates"] += got["certificates"]
        base["awards"] += got["awards"]
        base["activities"] += got["activities"]

    intro = "\n".join(sections.get("intro", [])).strip()
    if not intro:                                   # 맨 위 자기소개 문단 구제
        para = [l for l in head if len(l) > 30 and not EMAIL.search(l) and not PHONE.search(l)]
        intro = "\n".join(para[:4]).strip()
    if intro:
        schema.active_target(doc)["intro"] = intro

    # 이름이 뭉개진 항목 걸러내기 ('안안안' 처럼 PDF 에서 잘못 읽힌 글자)
    for key in ("certificates", "awards"):
        base[key] = [x for x in base[key] if not _looks_junk(x.get("name", ""))]
    base["skills"] = [x for x in base["skills"] if not _looks_junk(x.get("name", ""))]

    found = {
        "경력": len(base["experience"]), "프로젝트": len(base["projects"]),
        "학력": len(base["education"]), "자격증": len(base["certificates"]),
        "수상": len(base["awards"]), "어학": len(base["languages"]),
        "활동": len(base["activities"]), "역량": len(base["skills"]),
    }
    total = sum(found.values())
    person = base["person"]

    # 얼마나 믿을 만한 결과인지 — 화면에서 경고를 띄우는 기준.
    # 이름만 찾고 내용을 하나도 못 읽었으면 낮음이다. 그걸 '일부는 읽었다'고
    # 하면 사용자가 결과를 확인하지 않고 넘어가 버린다.
    if total == 0:
        confidence = "low"
    elif (base["experience"] or base["projects"]) and total >= 6:
        confidence = "high"
    else:
        confidence = "medium"

    report = {
        "found": found,
        "person": person,
        "sections_seen": [s for s in sections if s != "head" and sections[s]],
        "leftover": "\n".join(head).strip(),
        "raw": text,
        "total": total,
        "intro": intro,
        "confidence": confidence,
    }
    return doc, report


def _looks_junk(name):
    """같은 글자만 반복되거나 너무 짧은 이름."""
    s = re.sub(r"\s+", "", name or "")
    if len(s) < 2:
        return True
    return len(set(s)) == 1
