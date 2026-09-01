# -*- coding: utf-8 -*-
"""데이터 구조.

문서(doc) 하나 = 한 사람의 포트폴리오 전체.

    doc = {
      "schema": 2,
      "base":    내 이력 원본 (한 번만 쓰면 계속 재사용)
      "targets": 지원처별 맞춤 설정 (회사마다 하나씩)
      "active":  지금 편집 중인 지원처 id
    }

base 는 사실 데이터, targets 는 '그 사실을 어떻게 보여줄지'만 담습니다.
그래서 회사를 새로 추가해도 원본 이력은 절대 훼손되지 않습니다.
"""

from __future__ import annotations

import copy
import uuid

SCHEMA_VERSION = 2


# ---------------------------------------------------------------- 빈 문서
def empty_person():
    return {
        "name": "", "name_en": "", "birth": "", "phone": "", "email": "",
        "location": "", "photo": "", "job_title": "",
        "links": [],  # [{"label": "GitHub", "url": "..."}]
    }


def empty_base():
    return {
        "person": empty_person(),
        "education": [],    # {school, dept, period, note}
        "languages": [],    # {name, level, cert, date, bar}
        "skills": [],       # {name, bar, tags}
        "certificates": [],  # {name, org, date, tags}
        "awards": [],       # {name, prize, date, tags}
        "activities": [],   # {name, period, type, desc, tags}
        "experience": [],   # {id, org, role, type, period, duration, summary, points, tags}
        "projects": [],     # 아래 empty_project()
        "custom": {         # 자유 주제 섹션 (게임 이해도 / 직무 관점 등)
            "title": "", "subtitle": "", "items": []  # {q, hint, a}
        },
    }


def empty_project():
    return {
        "id": new_id("p"),
        "title": "", "subtitle": "", "subtitle_safe": "",
        "org": "", "period": "", "my_role": "",
        "image": "",
        "metric_value": "", "metric_label": "",
        "metric_value_safe": "", "metric_label_safe": "",
        "background": "",
        "actions": [],
        "result": "", "result_safe": "",
        "core_skills": [],
        "tags": [],
    }


def empty_experience():
    return {
        "id": new_id("e"),
        "org": "", "role": "", "type": "", "period": "", "duration": "",
        "summary": "", "points": [], "tags": [],
    }


def empty_target(label="새 지원처"):
    return {
        "label": label,
        "company": "", "position": "", "jd_url": "", "jd_text": "", "deadline": "",
        "hero_eyebrow": "", "hero_title": "", "hero_tagline": "", "intro": "",
        "metrics": [],           # {value, label} x 4
        "hide_numbers": True,    # 구체적 수치 숨김이 기본값
        "project_order": [],
        "project_visible": {},
        "project_emphasis": {},
        "experience_order": [],
        "custom_enabled": False,
        "overrides": {},         # {"proj.<id>.background": "고쳐 쓴 문장"}
        "accent": "#2C5F8A",
    }


def empty_doc():
    doc = {
        "schema": SCHEMA_VERSION,
        "base": empty_base(),
        "targets": {"default": empty_target("기본 포트폴리오")},
        "active": "default",
    }
    return doc


def new_id(prefix="t"):
    return prefix + uuid.uuid4().hex[:8]


# ---------------------------------------------------------------- 정합성
def normalize(doc):
    """불러온 JSON을 현재 스키마에 맞춰 보정한다 (없는 키 채우기)."""
    if not isinstance(doc, dict):
        return empty_doc()

    out = empty_doc()
    base = doc.get("base") or {}
    for key, default in empty_base().items():
        val = base.get(key, default)
        if key == "person":
            person = empty_person()
            person.update(val if isinstance(val, dict) else {})
            out["base"]["person"] = person
        elif key == "custom":
            custom = {"title": "", "subtitle": "", "items": []}
            custom.update(val if isinstance(val, dict) else {})
            out["base"]["custom"] = custom
        else:
            out["base"][key] = val if isinstance(val, list) else default

    # 프로젝트 · 경력에 빠진 키 채우기.
    # id 가 겹치면 결과물에서 한 건만 남고 나머지가 소리 없이 사라지므로,
    # 비어 있거나 이미 쓴 id 는 여기서 새로 발급한다.
    fixed, seen = [], set()
    for pr in out["base"]["projects"]:
        item = empty_project()
        item.update(pr if isinstance(pr, dict) else {})
        if not item.get("id") or item["id"] in seen:
            item["id"] = new_id("p")
        seen.add(item["id"])
        fixed.append(item)
    out["base"]["projects"] = fixed

    fixed, seen = [], set()
    for ex in out["base"]["experience"]:
        item = empty_experience()
        item.update(ex if isinstance(ex, dict) else {})
        if not item.get("id") or item["id"] in seen:
            item["id"] = new_id("e")
        seen.add(item["id"])
        fixed.append(item)
    out["base"]["experience"] = fixed

    targets = doc.get("targets") or {}
    if isinstance(targets, dict) and targets:
        out["targets"] = {}
        for tid, t in targets.items():
            item = empty_target()
            item.update(t if isinstance(t, dict) else {})
            out["targets"][tid] = item

    active = doc.get("active")
    out["active"] = active if active in out["targets"] else list(out["targets"])[0]
    return out


def clone(obj):
    return copy.deepcopy(obj)


# ---------------------------------------------------------------- 조회
def active_target(doc):
    return doc["targets"][doc["active"]]


def project_by_id(doc, pid):
    for pr in doc["base"]["projects"]:
        if pr["id"] == pid:
            return pr
    return None


def ordered_projects(doc, target):
    """지원처 설정의 순서 · 노출 여부를 반영한 프로젝트 목록."""
    projects = doc["base"]["projects"]
    order = [pid for pid in (target.get("project_order") or []) if project_by_id(doc, pid)]
    for pr in projects:                      # 순서에 없는 새 항목은 뒤에 붙인다
        if pr["id"] not in order:
            order.append(pr["id"])
    visible = target.get("project_visible") or {}
    return [project_by_id(doc, pid) for pid in order if visible.get(pid, True)]


def ordered_experience(doc, target):
    exps = doc["base"]["experience"]
    order = [eid for eid in (target.get("experience_order") or [])
             if any(e["id"] == eid for e in exps)]
    for ex in exps:
        if ex["id"] not in order:
            order.append(ex["id"])
    by_id = {e["id"]: e for e in exps}
    return [by_id[eid] for eid in order]


# ---------------------------------------------------------------- 태그
LANG_TAGS = {"영어": "영어", "English": "영어", "일본어": "일본어", "일어": "일본어",
             "중국어": "중국어", "중국": "중국어", "북경어": "중국어"}


def my_tags(doc):
    """내 이력 전체에서 모은 역량 태그."""
    out = []
    b = doc["base"]
    for group in ("experience", "projects", "skills", "certificates",
                  "awards", "activities", "languages"):
        for item in b.get(group) or []:
            for t in item.get("tags") or []:
                if t not in out:
                    out.append(t)

    # 어학은 따로 태그를 달지 않아도 언어 이름에서 자동으로 잡아 준다
    for lang in b.get("languages") or []:
        name = lang.get("name", "")
        for key, tag in LANG_TAGS.items():
            if key in name and tag not in out:
                out.append(tag)
    if b.get("languages") and "외국어" not in out:
        out.append("외국어")
    return out


def my_text(doc, target=None):
    """키워드 비교용 · 포트폴리오에 실제로 실리는 모든 문장."""
    b = doc["base"]
    chunks = []
    p = b["person"]
    chunks += [p.get("job_title", "")]
    for e in b["education"]:
        chunks += [e.get("school", ""), e.get("dept", ""), e.get("note", "")]
    for l in b["languages"]:
        chunks += [l.get("name", ""), l.get("level", ""), l.get("cert", "")]
    for s in b["skills"]:
        chunks.append(s.get("name", ""))
    for c in b["certificates"]:
        chunks += [c.get("name", ""), c.get("org", "")]
    for a in b["awards"]:
        chunks += [a.get("name", ""), a.get("prize", "")]
    for a in b["activities"]:
        chunks += [a.get("name", ""), a.get("type", ""), a.get("desc", "")]
    for e in b["experience"]:
        chunks += [e.get("org", ""), e.get("role", ""), e.get("summary", "")]
        chunks += e.get("points") or []
    for pr in b["projects"]:
        chunks += [pr.get("title", ""), pr.get("subtitle", ""), pr.get("org", ""),
                   pr.get("my_role", ""), pr.get("background", ""), pr.get("result", "")]
        chunks += pr.get("actions") or []
        chunks += pr.get("core_skills") or []
    for it in b["custom"].get("items") or []:
        chunks += [it.get("q", ""), it.get("a", "")]
    if target:
        chunks += [target.get("hero_title", ""), target.get("hero_tagline", ""),
                   target.get("intro", "")]
    return "\n".join(c for c in chunks if c)


# ---------------------------------------------------------------- 렌더용 뷰
def _ov(target, path, fallback):
    o = target.get("overrides") or {}
    return o[path] if path in o else fallback


def project_fields(pr, hide_numbers):
    """수치 표기 설정에 따라 원문 / 무수치 버전을 고른다."""
    def pick(key):
        safe = pr.get(key + "_safe")
        if hide_numbers and safe:
            return safe
        return pr.get(key, "")
    return {
        "subtitle": pick("subtitle"),
        "result": pick("result"),
        "metric_value": pick("metric_value"),
        "metric_label": pick("metric_label"),
    }


def build_view(doc, target=None):
    """HTML · PPT 가 그대로 쓰는 최종 데이터."""
    target = target or active_target(doc)
    hide = bool(target.get("hide_numbers", True))
    b = doc["base"]

    projects = []
    for pr in ordered_projects(doc, target):
        k = "proj." + pr["id"]
        f = project_fields(pr, hide)
        item = clone(pr)
        item.update({
            "title": _ov(target, k + ".title", pr.get("title", "")),
            "subtitle": _ov(target, k + ".subtitle", f["subtitle"]),
            "background": _ov(target, k + ".background", pr.get("background", "")),
            "result": _ov(target, k + ".result", f["result"]),
            "metric_value": _ov(target, k + ".metric_value", f["metric_value"]),
            "metric_label": _ov(target, k + ".metric_label", f["metric_label"]),
            "actions": [_ov(target, "%s.actions.%d" % (k, i), a)
                        for i, a in enumerate(pr.get("actions") or [])],
            "emphasis": (target.get("project_emphasis") or {}).get(pr["id"], ""),
        })
        projects.append(item)

    experience = []
    for ex in ordered_experience(doc, target):
        k = "exp." + ex["id"]
        item = clone(ex)
        item["summary"] = _ov(target, k + ".summary", ex.get("summary", ""))
        experience.append(item)

    custom = clone(b["custom"])
    custom["items"] = [it for it in (custom.get("items") or [])
                       if (it.get("a") or "").strip()]
    custom_on = bool(target.get("custom_enabled")) and bool(custom["items"])

    note = ""
    if target.get("company"):
        pos = target.get("position") or ""
        note = "%s %s 지원용으로 구성했습니다." % (target["company"], pos)

    return {
        "person": b["person"],
        "target": target,
        "hero": {
            "eyebrow": target.get("hero_eyebrow") or "Portfolio",
            "title": target.get("hero_title") or b["person"].get("name", ""),
            "tagline": target.get("hero_tagline", ""),
            "metrics": [m for m in (target.get("metrics") or []) if m.get("value") or m.get("label")],
        },
        "intro": target.get("intro", ""),
        "index_note": note,
        "experience": experience,
        "projects": projects,
        "custom": custom if custom_on else None,
        "skills": b["skills"],
        "languages": b["languages"],
        "certificates": b["certificates"],
        "education": b["education"],
        "awards": b["awards"],
        "activities": b["activities"],
        "accent": target.get("accent") or "#2C5F8A",
    }


def file_stem(doc, target=None):
    target = target or active_target(doc)
    name = doc["base"]["person"].get("name") or "포트폴리오"
    if target.get("company"):
        return "포트폴리오_%s_%s" % (name, target["company"])
    return "포트폴리오_%s" % name
