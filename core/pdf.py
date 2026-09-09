# -*- coding: utf-8 -*-
"""뷰 데이터 -> 진짜 PDF 파일.

브라우저 인쇄를 거치지 않고 서버에서 바로 PDF 를 만듭니다.
받는 사람 입장에서 'PDF 를 눌렀는데 html 이 떨어지는' 일이 없어야 하기 때문입니다.

한글 글꼴이 있어야 글자가 나옵니다. 시스템에 깔린 글꼴을 찾아 쓰고,
못 찾으면 만들지 않고 이유를 알려 줍니다 (네모만 찍힌 PDF 를 주는 것보다 낫습니다).
Streamlit Cloud 에서는 packages.txt 의 fonts-nanum 이 깔립니다.
"""

from __future__ import annotations

import base64
import io
import os
import re

from fpdf import FPDF

# ---------------------------------------------------------------- 색·치수
INK = (20, 24, 29)
INK_SOFT = (61, 72, 84)
MUTED = (107, 119, 133)
MUTED_2 = (152, 162, 173)
LINE = (227, 232, 237)
LINE_2 = (238, 241, 244)
BLUE = (44, 95, 138)
BLUE_LT = (74, 144, 194)
PAPER = (255, 255, 255)
WHITE = (255, 255, 255)

PAGE_W = 210.0
PAGE_H = 297.0
MARGIN = 16.0
BODY_W = PAGE_W - MARGIN * 2

# (보통, 굵게) 순서. 굵은 글꼴이 없으면 보통을 같이 씁니다.
FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
     "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"),
    ("/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
     "/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf"),
    ("C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf"),
    ("C:/Windows/Fonts/NanumGothic.ttf", "C:/Windows/Fonts/NanumGothicBold.ttf"),
    ("/Library/Fonts/NanumGothic.ttf", None),
    ("/System/Library/Fonts/Supplemental/AppleGothic.ttf", None),
]

_BUNDLED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "static", "fonts")


class FontMissing(RuntimeError):
    """한글 글꼴을 못 찾았을 때."""


def find_font():
    """(보통, 굵게) 글꼴 경로. 없으면 FontMissing."""
    bundled = (os.path.join(_BUNDLED, "NanumGothic.ttf"),
               os.path.join(_BUNDLED, "NanumGothicBold.ttf"))
    if os.path.exists(bundled[0]):
        return bundled[0], bundled[1] if os.path.exists(bundled[1]) else bundled[0]
    for regular, bold in FONT_CANDIDATES:
        if os.path.exists(regular):
            return regular, (bold if bold and os.path.exists(bold) else regular)
    raise FontMissing(
        "PDF 를 만들 한글 글꼴을 찾지 못했습니다. "
        "서버에 fonts-nanum 을 설치하거나 app/static/fonts/NanumGothic.ttf 를 넣어 주세요.")


def font_available():
    try:
        find_font()
        return True
    except FontMissing:
        return False


def _clean(text):
    """PDF 에 넣기 전에 줄바꿈·제어문자를 정리한다."""
    s = str(text or "")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    return s.strip()


def _image_bytes(data_uri):
    """data:image/... 만 받는다. 남이 보낸 문서의 외부 주소는 무시."""
    s = str(data_uri or "").strip()
    if not s.lower().startswith("data:image/"):
        return None
    try:
        return io.BytesIO(base64.b64decode(s.split(",", 1)[1]))
    except Exception:
        return None


# ---------------------------------------------------------------- 문서
class Doc(FPDF):
    def __init__(self, name):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.doc_name = name
        self.set_auto_page_break(True, margin=20)
        regular, bold = find_font()
        self.add_font("KR", "", regular)
        self.add_font("KR", "B", bold)
        self.set_title("%s · Portfolio" % name)

    # 페이지 아래 이름·쪽수
    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_font("KR", "", 8)
        self.set_text_color(*MUTED_2)
        self.cell(BODY_W / 2, 5, self.doc_name, align="L")
        self.cell(BODY_W / 2, 5, "%d" % self.page_no(), align="R")

    # ------------------------------------------------------------ 도우미
    def txt(self, text, size=10, bold=False, color=INK_SOFT, lh=5.2, w=None,
            align="L", after=0.0):
        text = _clean(text)
        if not text:
            return
        self.set_font("KR", "B" if bold else "", size)
        self.set_text_color(*color)
        self.set_x(MARGIN)
        self.multi_cell(w or BODY_W, lh, text, align=align)
        if after:
            self.ln(after)

    def room(self, mm):
        """남은 높이가 모자라면 다음 장으로."""
        if self.get_y() + mm > PAGE_H - 20:
            self.add_page()
            return True
        return False

    def rule(self, color=LINE, gap=3.0):
        self.ln(gap)
        self.set_draw_color(*color)
        self.set_line_width(0.2)
        y = self.get_y()
        self.line(MARGIN, y, PAGE_W - MARGIN, y)
        self.ln(gap)

    def section_head(self, num, label, title):
        self.room(30)
        self.ln(4)
        self.set_font("KR", "B", 8)
        self.set_text_color(*BLUE)
        self.set_x(MARGIN)
        self.cell(BODY_W, 4.5, "%02d / %s" % (num, label.upper()))
        self.ln(5)
        self.set_draw_color(*BLUE)
        self.set_line_width(0.6)
        y = self.get_y()
        self.line(MARGIN, y, MARGIN + 26, y)
        self.ln(3.5)
        self.txt(title, size=16, bold=True, color=INK, lh=7)
        self.ln(2.5)

    def label(self, text, color=MUTED_2, size=7.5, after=1.2):
        self.txt(text, size=size, bold=True, color=color, lh=3.8, after=after)

    def bullets(self, items, size=9.5):
        for it in items or []:
            it = _clean(it)
            if not it:
                continue
            self.room(10)
            self.set_font("KR", "", size)
            self.set_text_color(*INK_SOFT)
            self.set_x(MARGIN)
            self.cell(4, 4.8, "·")
            self.multi_cell(BODY_W - 4, 4.8, it, align="L")

    def chips(self, items, size=8):
        """알약 모양 태그를 줄바꿈해 가며 배치."""
        items = [_clean(x) for x in (items or []) if _clean(x)]
        if not items:
            return
        self.set_font("KR", "", size)
        x, y = MARGIN, self.get_y()
        h = 5.6
        for it in items:
            w = self.get_string_width(it) + 6
            if x + w > PAGE_W - MARGIN:
                x = MARGIN
                y += h + 1.6
                if y + h > PAGE_H - 20:
                    self.add_page()
                    y = self.get_y()
            self.set_fill_color(247, 249, 251)
            self.set_draw_color(*LINE)
            self.set_line_width(0.2)
            self.rect(x, y, w, h, style="DF")
            self.set_text_color(*INK_SOFT)
            self.set_xy(x, y)
            self.cell(w, h, it, align="C")
            x += w + 2
        self.set_y(y + h + 2)

    def bar(self, name, note, pct):
        """역량 막대 하나."""
        self.room(14)
        y = self.get_y()
        self.set_font("KR", "B", 9.5)
        self.set_text_color(*INK)
        self.set_xy(MARGIN, y)
        self.cell(BODY_W * 0.62, 4.6, _clean(name))
        if note:
            self.set_font("KR", "", 8.5)
            self.set_text_color(*MUTED)
            self.cell(BODY_W * 0.38, 4.6, _clean(note), align="R")
        y += 5.6
        pct = max(0, min(100, int(pct or 0)))
        self.set_fill_color(*LINE_2)
        self.rect(MARGIN, y, BODY_W, 1.8, style="F")
        if pct:
            self.set_fill_color(*BLUE)
            self.rect(MARGIN, y, BODY_W * pct / 100.0, 1.8, style="F")
        self.set_y(y + 5.4)


# ---------------------------------------------------------------- 표지
def _cover(d, v):
    d.add_page()
    hero_h = 118.0
    d.set_fill_color(*INK)
    d.rect(0, 0, PAGE_W, hero_h, style="F")

    # 왼쪽 세로선
    d.set_fill_color(*BLUE_LT)
    d.rect(MARGIN, 22, 0.9, 34, style="F")

    y = 24.0
    eyebrow = _clean(v["hero"].get("eyebrow"))
    if eyebrow:
        d.set_font("KR", "B", 8)
        d.set_text_color(150, 190, 225)
        d.set_xy(MARGIN + 4, y)
        d.cell(BODY_W - 4, 4, eyebrow.upper())
        y += 8.0

    title = _clean(v["hero"].get("title")) or _clean(v["person"].get("name")) or "Portfolio"
    d.set_font("KR", "B", 21)
    d.set_text_color(*WHITE)
    for line in title.split("\n")[:3]:
        d.set_xy(MARGIN + 4, y)
        d.cell(BODY_W - 4, 9.5, line.strip())
        y += 10.0

    tagline = _clean(v["hero"].get("tagline"))
    if tagline:
        y += 3.0
        d.set_font("KR", "", 10)
        d.set_text_color(196, 206, 216)
        d.set_xy(MARGIN + 4, y)
        d.multi_cell(BODY_W - 20, 5.4, tagline, align="L")
        y = d.get_y() + 3.0

    # 연락처 줄
    p = v["person"]
    meta = [p.get("birth"), p.get("location"), p.get("email"), p.get("phone")]
    meta += [l.get("label") for l in (p.get("links") or [])]
    meta = [_clean(x) for x in meta if _clean(x)]
    if meta:
        d.set_font("KR", "", 8.5)
        x = MARGIN + 4
        for m in meta:
            w = d.get_string_width(m) + 7
            if x + w > PAGE_W - MARGIN:
                x = MARGIN + 4
                y += 8.0
            d.set_draw_color(70, 84, 98)
            d.set_line_width(0.2)
            d.rect(x, y, w, 6.6, style="D")
            d.set_text_color(205, 214, 223)
            d.set_xy(x, y)
            d.cell(w, 6.6, m, align="C")
            x += w + 2.5
        y += 12.0

    # 지표 카드
    metrics = (v["hero"].get("metrics") or [])[:4]
    if metrics:
        card_y = min(y, hero_h - 30)
        gap = 2.5
        cw = (BODY_W - gap * (len(metrics) - 1)) / len(metrics)
        for i, m in enumerate(metrics):
            cx = MARGIN + i * (cw + gap)
            d.set_fill_color(30, 38, 47)
            d.rect(cx, card_y, cw, 21, style="F")
            d.set_font("KR", "B", 14)
            d.set_text_color(*BLUE_LT)
            d.set_xy(cx + 4, card_y + 3.5)
            d.cell(cw - 8, 7, _clean(m.get("value")))
            d.set_font("KR", "", 7.5)
            d.set_text_color(160, 172, 184)
            d.set_xy(cx + 4, card_y + 12)
            d.cell(cw - 8, 4, _clean(m.get("label")))

    d.set_y(hero_h + 8)


# ---------------------------------------------------------------- 섹션
def _about(d, v, n):
    d.section_head(n, "About", "저를 소개합니다")
    photo = _image_bytes(v["person"].get("photo"))
    intro = _clean(v.get("intro"))
    if photo:
        try:
            top = d.get_y()
            d.image(photo, x=MARGIN, y=top, w=30)
            d.set_xy(MARGIN + 34, top)
            d.set_font("KR", "", 10)
            d.set_text_color(*INK_SOFT)
            d.multi_cell(BODY_W - 34, 5.4, intro, align="L")
            d.set_y(max(d.get_y(), top + 40))
            return
        except Exception:
            pass                      # 사진이 깨져 있으면 글만 넣는다
    d.txt(intro, size=10, lh=5.4)


def _experience(d, v, n):
    d.section_head(n, "Experience", "경력 사항")
    for ex in v["experience"]:
        d.room(34)
        head = " · ".join(x for x in [_clean(ex.get("org")), _clean(ex.get("role"))] if x)
        d.txt(head, size=11.5, bold=True, color=INK, lh=5.6)
        sub = " · ".join(x for x in [_clean(ex.get("period")), _clean(ex.get("duration")),
                                     _clean(ex.get("type"))] if x)
        d.txt(sub, size=8.5, color=MUTED, lh=4.2, after=1.0)
        d.txt(ex.get("summary"), size=9.5, lh=4.9)
        d.bullets(ex.get("points"))
        d.rule(LINE_2, gap=2.6)


def _projects(d, v, n):
    d.section_head(n, "Projects", "주요 프로젝트")
    for i, pr in enumerate(v["projects"], 1):
        d.room(46)
        d.label("PROJECT %02d" % i, color=BLUE)
        d.txt(pr.get("title"), size=13, bold=True, color=INK, lh=6.2)
        d.txt(pr.get("subtitle") or pr.get("subtitle_safe"), size=9.5,
              bold=True, color=BLUE, lh=4.8)
        meta = " · ".join(x for x in [_clean(pr.get("org")), _clean(pr.get("period")),
                                      _clean(pr.get("my_role"))] if x)
        d.txt(meta, size=8.5, color=MUTED_2, lh=4.2, after=1.4)

        val, lab = pr.get("metric_value"), pr.get("metric_label")
        if val and lab:
            d.room(16)
            y = d.get_y()
            d.set_fill_color(246, 250, 254)
            d.rect(MARGIN, y, BODY_W, 13, style="F")
            d.set_font("KR", "B", 13)
            d.set_text_color(*BLUE)
            d.set_xy(MARGIN + 4, y + 1.6)
            d.cell(50, 6, _clean(val))
            d.set_font("KR", "", 8)
            d.set_text_color(*MUTED)
            d.set_xy(MARGIN + 4, y + 7.8)
            d.cell(BODY_W - 8, 4, _clean(lab))
            d.set_y(y + 16)

        for key, name in (("background", "BACKGROUND"), ("result", "RESULT")):
            body = _clean(pr.get(key))
            if body:
                d.room(16)
                d.label(name)
                d.txt(body, size=9.5, lh=4.9, after=1.2)
        if pr.get("actions"):
            d.room(16)
            d.label("ACTION")
            d.bullets(pr["actions"])
            d.ln(1.2)
        if pr.get("core_skills"):
            d.room(12)
            d.chips(pr["core_skills"])
        d.rule(LINE, gap=3.0)


def _custom(d, v, n):
    c = v["custom"]
    title = _clean(c.get("title")) or "제품을 보는 관점"
    d.section_head(n, "Perspective", title)
    # 부제는 제목이 아니라 안내문이므로 작게 깐다
    d.txt(c.get("subtitle"), size=9.5, color=MUTED, lh=4.8, after=1.5)
    for it in c.get("items") or []:
        if not _clean(it.get("a")):
            continue
        d.room(24)
        d.txt(it.get("q"), size=10.5, bold=True, color=INK, lh=5.2)
        d.txt(it.get("a"), size=9.5, lh=4.9, after=2.0)


def _skills(d, v, n):
    d.section_head(n, "Skills & Languages", "보유 역량")
    if v["skills"]:
        d.label("TOOLS & SKILLS", after=2.0)
        for s in v["skills"]:
            d.bar(s.get("name"), "", s.get("bar"))
        d.ln(1.5)
    if v["languages"]:
        d.label("LANGUAGES", after=2.0)
        for l in v["languages"]:
            note = " · ".join(x for x in [_clean(l.get("level")), _clean(l.get("cert"))] if x)
            d.bar(l.get("name"), note, l.get("bar"))
        d.ln(1.5)
    if v["certificates"]:
        d.label("CERTIFICATES", after=2.0)
        for c in v["certificates"]:
            d.room(9)
            y = d.get_y()
            d.set_font("KR", "B", 9.5)
            d.set_text_color(*INK)
            d.set_xy(MARGIN, y)
            d.cell(BODY_W * 0.6, 5, _clean(c.get("name")))
            d.set_font("KR", "", 8.5)
            d.set_text_color(*MUTED)
            d.cell(BODY_W * 0.4, 5, " · ".join(
                x for x in [_clean(c.get("org")), _clean(c.get("date"))] if x), align="R")
            d.set_y(y + 6)


def _more(d, v, n):
    d.section_head(n, "Education & Activities", "학력 · 수상 · 활동")
    if v["education"]:
        d.label("EDUCATION", after=2.0)
        for e in v["education"]:
            d.room(12)
            d.txt(" · ".join(x for x in [_clean(e.get("school")), _clean(e.get("dept"))] if x),
                  size=10, bold=True, color=INK, lh=5)
            d.txt(" · ".join(x for x in [_clean(e.get("period")), _clean(e.get("note"))] if x),
                  size=8.5, color=MUTED, lh=4.2, after=1.5)
    if v["awards"]:
        d.label("AWARDS", after=2.0)
        for a in v["awards"]:
            d.room(11)
            d.txt(" · ".join(x for x in [_clean(a.get("name")), _clean(a.get("prize"))] if x),
                  size=10, bold=True, color=INK, lh=5)
            d.txt(_clean(a.get("date")), size=8.5, color=MUTED, lh=4.2, after=1.5)
    if v["activities"]:
        d.label("ACTIVITIES", after=2.0)
        for a in v["activities"]:
            d.room(16)
            d.txt(a.get("name"), size=10, bold=True, color=INK, lh=5)
            d.txt(a.get("desc"), size=9.5, lh=4.8)
            d.txt(" · ".join(x for x in [_clean(a.get("type")), _clean(a.get("period"))] if x),
                  size=8.5, color=MUTED_2, lh=4.2, after=2.0)


def _contact(d, v):
    p = v["person"]
    bits = [_clean(p.get("email")), _clean(p.get("phone"))]
    bits += [_clean(l.get("url")) for l in (p.get("links") or [])]
    bits = [b for b in bits if b]
    if not bits:
        return
    d.room(34)
    d.ln(4)
    # 새 장이 열려 혼자 남았으면 띄우지 말고 아래로 내린다
    if d.get_y() < 45:
        d.set_y(PAGE_H - 48)
    y = d.get_y()
    d.set_fill_color(*INK)
    d.rect(0, y, PAGE_W, 30, style="F")
    d.set_font("KR", "B", 8)
    d.set_text_color(150, 190, 225)
    d.set_xy(MARGIN, y + 5)
    d.cell(BODY_W, 4, "CONTACT", align="C")
    d.set_font("KR", "B", 12)
    d.set_text_color(*WHITE)
    d.set_xy(MARGIN, y + 11)
    d.cell(BODY_W, 6, "읽어주셔서 감사합니다.", align="C")
    d.set_font("KR", "", 9)
    d.set_text_color(185, 196, 207)
    d.set_xy(MARGIN, y + 19)
    d.cell(BODY_W, 5, "  ·  ".join(bits[:3]), align="C")
    d.set_y(y + 32)


# ---------------------------------------------------------------- 진입점
def build(v):
    """뷰 데이터로 PDF 를 만들어 BytesIO 로 돌려준다."""
    name = _clean(v["person"].get("name")) or "Portfolio"
    d = Doc(name)
    _cover(d, v)

    num = 0
    if _clean(v.get("intro")) or v["person"].get("photo"):
        num += 1
        _about(d, v, num)
    if v["experience"]:
        num += 1
        _experience(d, v, num)
    if v["projects"]:
        num += 1
        _projects(d, v, num)
    if v["custom"] and (v["custom"].get("items") or []):
        num += 1
        _custom(d, v, num)
    if v["skills"] or v["languages"] or v["certificates"]:
        num += 1
        _skills(d, v, num)
    if v["education"] or v["awards"] or v["activities"]:
        num += 1
        _more(d, v, num)
    _contact(d, v)

    return io.BytesIO(bytes(d.output()))
