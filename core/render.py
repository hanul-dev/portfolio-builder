# -*- coding: utf-8 -*-
"""뷰 데이터 -> 단독 실행 가능한 HTML 포트폴리오.

이미지는 data URI 로 들어가므로 결과 파일 하나만 있으면
인터넷 없이도 열리고, 그대로 메일에 첨부해도 됩니다.
"""

from __future__ import annotations

import html
import re
import os

_CSS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "static", "portfolio.css")


def _css():
    with open(_CSS_PATH, encoding="utf-8") as f:
        return f.read()


def e(text):
    return html.escape(str(text or ""), quote=True)


def nl2br(text):
    return e(text).replace("\n", "<br>")


def safe_img(src):
    """이미지 자리에는 우리가 만든 data URI 만 허용한다.

    남이 보낸 JSON 을 불러왔을 때 엉뚱한 주소가 끼어들지 않도록 막습니다.
    """
    s = str(src or "").strip()
    return e(s) if s.lower().startswith("data:image/") else ""


_OK_SCHEMES = ("http://", "https://", "mailto:", "tel:")


def safe_url(url):
    """javascript: 같은 실행형 주소를 걸러낸다."""
    s = str(url or "").strip()
    if s.lower().startswith(_OK_SCHEMES):
        return e(s)
    if s and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", s):
        return e("https://" + s)          # 스킴 없이 적었으면 https 로 붙여 준다
    return ""


# ---------------------------------------------------------------- 섹션
def _hero(v):
    p = v["person"]
    meta = []
    if p.get("birth"):
        meta.append(p["birth"])
    if p.get("location"):
        meta.append(p["location"])
    if p.get("email"):
        meta.append(p["email"])
    if p.get("phone"):
        meta.append(p["phone"])
    for link in p.get("links") or []:
        if link.get("label"):
            meta.append(link["label"])

    metrics = ""
    if v["hero"]["metrics"]:
        cells = "".join(
            "<div><b>%s</b><small>%s</small></div>" % (e(m.get("value", "")), e(m.get("label", "")))
            for m in v["hero"]["metrics"][:4])
        metrics = '<div class="hero-metrics">%s</div>' % cells

    return """
<section class="hero">
  <div class="hero-bg"></div><div class="hero-grid"></div>
  <div class="hero-in">
    <div class="hero-frame">
      <span class="hero-eyebrow">%s</span>
      <h1 class="hero-title">%s</h1>
      <p class="hero-tagline">%s</p>
      <div class="hero-meta">%s</div>
    </div>
    %s
  </div>
</section>""" % (
        e(v["hero"]["eyebrow"]),
        e(v["hero"]["title"]),
        e(v["hero"]["tagline"]),
        "".join("<span>%s</span>" % e(m) for m in meta),
        metrics,
    )


def _sections_plan(v):
    """실제로 내용이 있는 섹션만 목차에 올린다."""
    plan = []
    if v["intro"] or v["person"].get("photo"):
        plan.append(("about", "About", "저를 소개합니다"))
    if v["experience"]:
        plan.append(("experience", "Experience", "경력 사항"))
    if v["projects"]:
        plan.append(("projects", "Projects", "주요 프로젝트"))
    if v["custom"]:
        title = v["custom"].get("title") or "Perspective"
        plan.append(("custom", title, v["custom"].get("subtitle") or "직무에 대한 관점"))
    if v["skills"] or v["languages"] or v["certificates"]:
        plan.append(("skills", "Skills & Languages", "보유 역량"))
    if v["education"] or v["awards"] or v["activities"]:
        plan.append(("more", "Education & Activities", "학력 · 수상 · 활동"))
    return plan


def _index(v, plan):
    if not plan:
        return ""
    items = "".join(
        '<li><span class="n">%02d</span><div><span class="t">%s</span>'
        '<span class="d">%s</span></div></li>' % (i + 1, e(t), e(d))
        for i, (_sid, t, d) in enumerate(plan))
    return """
<section id="index">
  <div class="wrap"><div class="index-layout">
    <div><div class="index-badge">INDEX</div><p class="index-note">%s</p></div>
    <ul class="index-list">%s</ul>
  </div></div>
</section>""" % (e(v["index_note"]), items)


def _sec_head(num, label, title, sub=""):
    return """<div class="sec-head">
      <span class="sec-num">%02d / %s</span>
      <h2 class="sec-title">%s</h2>
      %s
    </div>""" % (num, e(label.upper()), e(title),
                 ('<p class="sec-sub">%s</p>' % e(sub)) if sub else "")


def _about(v, num):
    p = v["person"]
    rows = []
    if p.get("birth"):
        rows.append(("생년", e(p["birth"])))
    if p.get("location"):
        rows.append(("거주지", e(p["location"])))
    if p.get("phone"):
        rows.append(("연락처", '<a href="tel:%s">%s</a>' % (e(p["phone"]), e(p["phone"]))))
    if p.get("email"):
        rows.append(("이메일", '<a href="mailto:%s">%s</a>' % (e(p["email"]), e(p["email"]))))
    for link in p.get("links") or []:
        if link.get("url"):
            rows.append((e(link.get("label") or "링크"),
                         '<a href="%s">%s</a>' % (safe_url(link["url"]), e(link["url"]))))

    photo = ('<img src="%s" alt="%s 프로필 사진">' % (safe_img(p["photo"]), e(p.get("name", "")))
             if p.get("photo") else "")
    card = """<div class="about-idcard">
        <div class="nm">%s <small>%s</small></div>%s
      </div>""" % (
        e(p.get("name", "")), e(p.get("name_en", "")),
        "".join('<div class="row"><b>%s</b><span>%s</span></div>' % (k, val) for k, val in rows))

    strengths = ""
    if v["projects"]:
        cards = []
        for pr in v["projects"][:4]:
            if pr.get("core_skills"):
                cards.append('<div class="strength"><b>%s</b><span>%s</span></div>' % (
                    e(pr["core_skills"][0]),
                    e(pr.get("subtitle") or pr.get("title", ""))))
        if cards:
            strengths = '<div class="strength-grid">%s</div>' % "".join(cards)

    return """
<section id="about" class="alt"><div class="wrap">
  %s
  <div class="about-layout">
    <div class="about-photo">%s%s</div>
    <div><p class="about-intro">%s</p>%s</div>
  </div>
</div></section>""" % (_sec_head(num, "About", "저를 소개합니다"), photo, card,
                       nl2br(v["intro"]), strengths)


def _experience(v, num):
    rows = []
    for ex in v["experience"]:
        points = ""
        if ex.get("points"):
            points = '<ul class="exp-points">%s</ul>' % "".join(
                "<li>%s</li>" % e(pt) for pt in ex["points"] if pt)
        dur = ('<span class="exp-dur">%s</span>' % e(ex["duration"])) if ex.get("duration") else ""
        rows.append("""<div class="exp">
        <div><div class="exp-when">%s</div>%s</div>
        <div>
          <h3 class="exp-org">%s</h3>
          <p class="exp-role">%s%s</p>
          <p class="exp-sum">%s</p>%s
        </div>
      </div>""" % (e(ex.get("period", "")), dur, e(ex.get("org", "")), e(ex.get("role", "")),
                   (" · %s" % e(ex["type"])) if ex.get("type") else "",
                   e(ex.get("summary", "")), points))
    return """
<section id="experience" class="dark"><div class="wrap">
  %s<div class="exp-list">%s</div>
</div></section>""" % (_sec_head(num, "Experience", "경력 사항"), "".join(rows))


def _projects(v, num):
    cards = []
    for i, pr in enumerate(v["projects"]):
        metric = ""
        if pr.get("metric_value"):
            metric = '<div class="proj-metric"><b>%s</b><span>%s</span></div>' % (
                e(pr["metric_value"]), e(pr.get("metric_label", "")))

        meta = " · ".join(x for x in [pr.get("org", ""), pr.get("period", ""), pr.get("my_role", "")] if x)

        actions = ""
        if pr.get("actions"):
            actions = ('<p class="proj-label">ACTION</p><ul class="proj-actions">%s</ul>'
                       % "".join("<li>%s</li>" % e(a) for a in pr["actions"] if a))

        figure = ""
        if pr.get("image"):
            figure = '<div class="proj-figure"><img src="%s" alt="%s"></div>' % (
                safe_img(pr["image"]), e(pr.get("title", "")))
        skills = ""
        if pr.get("core_skills"):
            skills = '<div class="proj-skills">%s</div>' % "".join(
                "<span>%s</span>" % e(s) for s in pr["core_skills"])

        result = ""
        if pr.get("result"):
            result = ('<div class="proj-result"><div class="k">RESULT</div>'
                      '<p>%s</p></div>' % e(pr["result"]))
        emphasis = ""
        if pr.get("emphasis"):
            emphasis = '<div class="proj-emphasis"><b>이 프로젝트를 앞에 둔 이유 —</b> %s</div>' % e(pr["emphasis"])

        background = ""
        if pr.get("background"):
            background = '<p class="proj-label">BACKGROUND</p><p class="proj-text">%s</p>' % e(pr["background"])

        cards.append("""<article class="proj">
        <div class="proj-top">
          <div>
            <span class="proj-no">PROJECT %02d</span>
            <h3 class="proj-title">%s</h3>
            <p class="proj-sub">%s</p>
            <p class="proj-meta">%s</p>
          </div>%s
        </div>
        <div class="proj-body">
          <div>%s%s</div>
          <div>%s%s</div>
        </div>
        %s%s
      </article>""" % (i + 1, e(pr.get("title", "")), e(pr.get("subtitle", "")), e(meta),
                       metric, background, actions, figure, skills, result, emphasis))

    return """
<section id="projects"><div class="wrap">
  %s<div class="proj-list">%s</div>
</div></section>""" % (
        _sec_head(num, "Projects", "주요 프로젝트", "배경 → 실행 → 성과 순으로 정리했습니다."),
        "".join(cards))


def _custom(v, num):
    c = v["custom"]
    items = "".join(
        '<div class="free-item"><p class="free-q">%s</p><p class="free-a">%s</p></div>'
        % (e(it.get("q", "")), nl2br(it.get("a", "")))
        for it in c["items"])
    return """
<section id="custom" class="dark"><div class="wrap">
  %s<div class="free-grid">%s</div>
</div></section>""" % (
        _sec_head(num, "Perspective", c.get("title") or "직무에 대한 관점",
                  c.get("subtitle", "")),
        items)


def _bar(name, level, pct):
    return """<div class="bar-row">
      <div class="bar-head"><b>%s</b><span>%s</span></div>
      <div class="bar"><i style="width:%d%%"></i></div>
    </div>""" % (e(name), e(level), max(0, min(100, int(pct or 0))))


def _skills(v, num):
    left = ""
    if v["skills"]:
        left = '<p class="proj-label">TOOLS &amp; SKILLS</p>' + "".join(
            _bar(s.get("name", ""), "", s.get("bar", 80)) for s in v["skills"])
    right = ""
    if v["languages"]:
        right += '<p class="proj-label">LANGUAGES</p>' + "".join(
            _bar(l.get("name", ""), " ".join(x for x in [l.get("level", ""), l.get("cert", "")] if x),
                 l.get("bar", 80)) for l in v["languages"])
    if v["certificates"]:
        right += ('<p class="proj-label" style="margin-top:30px">CERTIFICATES</p>'
                  '<div class="mini-grid">%s</div>' % "".join(
                      '<div class="mini"><b>%s</b><span>%s</span></div>' % (
                          e(c.get("name", "")),
                          " · ".join(x for x in [c.get("org", ""), c.get("date", "")] if x))
                      for c in v["certificates"]))
    return """
<section id="skills" class="alt"><div class="wrap">
  %s<div class="skill-cols"><div>%s</div><div>%s</div></div>
</div></section>""" % (_sec_head(num, "Skills & Languages", "보유 역량"), left, right)


def _more(v, num):
    blocks = []
    if v["education"]:
        blocks.append(("Education", "".join(
            '<div class="info-item"><b>%s</b><span>%s</span><em>%s</em></div>' % (
                e(x.get("school", "")), e(x.get("dept", "")),
                " · ".join(y for y in [x.get("period", ""), x.get("note", "")] if y))
            for x in v["education"])))
    if v["awards"]:
        blocks.append(("Awards", "".join(
            '<div class="info-item"><b>%s</b><span>%s</span><em>%s</em></div>' % (
                e(x.get("name", "")), e(x.get("prize", "")), e(x.get("date", "")))
            for x in v["awards"])))
    if v["activities"]:
        blocks.append(("Activities", "".join(
            '<div class="info-item"><b>%s</b><span>%s</span><em>%s</em></div>' % (
                e(x.get("name", "")), e(x.get("desc", "")),
                " · ".join(y for y in [x.get("type", ""), x.get("period", "")] if y))
            for x in v["activities"])))
    if not blocks:
        return ""
    cols = "".join('<div class="info-block"><h3>%s</h3>%s</div>' % (t, body) for t, body in blocks)
    return """
<section id="more"><div class="wrap">
  %s<div class="info-grid">%s</div>
</div></section>""" % (_sec_head(num, "Education & Activities", "학력 · 수상 · 활동"), cols)


def _contact(v):
    p = v["person"]
    links = []
    if p.get("email"):
        links.append('<a class="contact-btn primary" href="mailto:%s">%s</a>' % (e(p["email"]), e(p["email"])))
    if p.get("phone"):
        links.append('<a class="contact-btn" href="tel:%s">%s</a>' % (e(p["phone"]), e(p["phone"])))
    for link in p.get("links") or []:
        if link.get("url"):
            links.append('<a class="contact-btn" href="%s">%s</a>' % (safe_url(link["url"]), e(link.get("label") or "링크")))
    return """
<section class="dark contact"><div class="wrap">
  <span class="eyebrow">Contact</span>
  <h2>읽어주셔서 감사합니다.</h2>
  <p>궁금한 점이 있다면 언제든 편하게 연락 주세요.</p>
  <div class="contact-links">%s</div>
</div></section>""" % "".join(links)


# ---------------------------------------------------------------- 전체
def render_html(v, standalone=True):
    plan = _sections_plan(v)
    body = [_hero(v), _index(v, plan)]
    num = 0
    for sid, label, title in plan:
        num += 1
        if sid == "about":
            body.append(_about(v, num))
        elif sid == "experience":
            body.append(_experience(v, num))
        elif sid == "projects":
            body.append(_projects(v, num))
        elif sid == "custom":
            body.append(_custom(v, num))
        elif sid == "skills":
            body.append(_skills(v, num))
        elif sid == "more":
            body.append(_more(v, num))
    body.append(_contact(v))

    name = v["person"].get("name") or "Portfolio"
    accent = v.get("accent") or "#2c5f8a"
    title = "%s · Portfolio" % name

    font_link = ""
    if standalone:
        font_link = (
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard'
            '@v1.3.9/dist/web/variable/pretendardvariable.min.css">'
            '<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800'
            '&display=swap" rel="stylesheet">')

    return """<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
%s
<style>
%s
:root { --accent: %s; }
</style>
</head><body>
%s
<footer><div class="wrap"><div>&copy; %s</div><div>Portfolio</div></div></footer>
</body></html>""" % (e(title), font_link, _css(), e(accent), "\n".join(body), e(name))
