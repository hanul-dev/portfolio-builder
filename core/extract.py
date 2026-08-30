# -*- coding: utf-8 -*-
"""파일과 링크에서 글자만 뽑아내는 층.

여기서는 '읽기'만 합니다. 읽은 글을 이력 항목으로 나누는 일은
parse_resume.py 가 맡습니다.
"""

from __future__ import annotations

import io
import logging
import re

# pdfminer 는 폰트가 조금만 특이해도 경고를 쏟아냅니다.
# 읽기 결과에는 영향이 없으므로 로그만 막아 둡니다.
for _name in ("pdfminer", "pdfminer.pdffont", "pdfminer.pdfinterp",
              "pdfminer.pdfpage", "pdfplumber"):
    logging.getLogger(_name).setLevel(logging.ERROR)

# ---------------------------------------------------------------- 파일
SUPPORTED = {"pdf": "PDF", "docx": "Word"}


def file_text(raw, filename):
    """업로드한 파일에서 글자를 뽑는다. -> (텍스트, 오류메시지)"""
    ext = (filename or "").rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        return _pdf_text(raw)
    if ext == "docx":
        return _docx_text(raw)
    if ext == "doc":
        return "", ("옛날 Word 형식(.doc)은 읽을 수 없습니다. "
                    "Word 에서 열어 .docx 나 PDF 로 저장한 뒤 올려 주세요.")
    if ext == "hwp":
        return "", ("한글 파일(.hwp)은 읽을 수 없습니다. 한글에서 "
                    "`파일 → 다른 이름으로 저장 → PDF` 로 저장해 올려 주세요.")
    if ext == "txt":
        try:
            return raw.decode("utf-8"), None
        except UnicodeDecodeError:
            try:
                return raw.decode("cp949"), None
            except Exception:
                return "", "글자 인코딩을 알 수 없습니다."
    return "", "PDF 또는 Word(.docx) 파일만 읽을 수 있습니다."


def _pdf_text(raw):
    try:
        import pdfplumber
    except ImportError:
        return "", "pdfplumber 가 설치되지 않았습니다. `pip install pdfplumber`"

    try:
        pages = []
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
                # 표 안에 이력이 들어 있는 이력서가 흔해서 같이 훑는다
                for table in page.extract_tables() or []:
                    for row in table:
                        cells = [c.strip() for c in row if c and c.strip()]
                        if cells:
                            pages.append("  ".join(cells))
        text = "\n".join(pages)
    except Exception as exc:
        return "", "PDF 를 여는 데 실패했습니다: %s" % exc

    if not text.strip():
        return "", ("글자를 찾지 못했습니다. 스캔한 이미지로 만든 PDF 같습니다. "
                    "글자를 선택할 수 있는 PDF 로 다시 저장하거나, 아래에 직접 붙여넣어 주세요.")
    return text, None


def _docx_text(raw):
    try:
        import docx
    except ImportError:
        return "", "python-docx 가 설치되지 않았습니다. `pip install python-docx`"

    try:
        d = docx.Document(io.BytesIO(raw))
        parts = [p.text for p in d.paragraphs]
        for table in d.tables:                      # 표로 짠 이력서 대응
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    parts.append("  ".join(dict.fromkeys(cells)))
        text = "\n".join(parts)
    except Exception as exc:
        return "", "Word 파일을 여는 데 실패했습니다: %s" % exc

    if not text.strip():
        return "", "내용이 비어 있습니다."
    return text, None


# ---------------------------------------------------------------- 링크
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_DROP_TAGS = ["script", "style", "noscript", "nav", "header", "footer",
              "form", "svg", "iframe", "aside"]


_HEADERS = {
    "User-Agent": _UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "no-cache",
}

# 공고 본문이면 거의 반드시 들어 있는 말들
JD_HINTS = ("자격요건", "담당업무", "우대사항", "주요업무", "지원자격", "모집부문",
            "업무내용", "필수요건", "지원자", "채용", "경력", "신입",
            "responsibilities", "qualifications", "requirements", "preferred")


def _score_jd(text):
    """이 글이 채용 공고 본문일 가능성 점수."""
    if not text:
        return 0
    low = text.lower()
    hits = sum(1 for h in JD_HINTS if h.lower() in low)
    return hits * 500 + min(len(text), 6000)


def _from_jsonld(html):
    """구글 채용검색용 JobPosting 구조화 데이터. 있으면 가장 깨끗하다."""
    import json
    best = ""
    for m in re.finditer(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>",
                         html or "", re.S | re.I):
        try:
            data = json.loads(m.group(1).strip())
        except Exception:
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                types = node.get("@type") or ""
                types = types if isinstance(types, str) else " ".join(map(str, types))
                if "JobPosting" in types:
                    parts = [node.get("title") or "",
                             html_to_text(node.get("description") or "")]
                    cand = "\n".join(p for p in parts if p)
                    if _score_jd(cand) > _score_jd(best):
                        best = cand
                stack.extend(v for v in node.values()
                             if isinstance(v, (dict, list)))
    return best


def _walk_strings(node, out, depth=0):
    if depth > 12:
        return
    if isinstance(node, str):
        if len(node) >= 120:
            out.append(node)
    elif isinstance(node, list):
        for v in node:
            _walk_strings(v, out, depth + 1)
    elif isinstance(node, dict):
        for v in node.values():
            _walk_strings(v, out, depth + 1)


def _from_embedded_json(html):
    """__NEXT_DATA__ 같은 스크립트에 박힌 JSON 에서 공고 본문을 찾는다.

    요즘 채용 사이트는 화면을 자바스크립트로 그리지만,
    그 재료가 되는 데이터는 HTML 안에 JSON 으로 같이 실려 옵니다.
    """
    import json
    best = ""
    blocks = re.findall(r"<script[^>]*>(.*?)</script>", html or "", re.S | re.I)
    for block in blocks:
        block = block.strip()
        if len(block) < 200 or ("{" not in block):
            continue
        # 통째로 JSON 이거나, `... = {...};` 형태
        candidates = [block]
        m = re.search(r"=\s*(\{.*\})\s*;?\s*$", block, re.S)
        if m:
            candidates.append(m.group(1))
        for raw in candidates:
            try:
                data = json.loads(raw)
            except Exception:
                continue
            strings = []
            _walk_strings(data, strings)
            for s in strings:
                cand = html_to_text(s) if "<" in s else s
                if _score_jd(cand) > _score_jd(best):
                    best = cand
            break
    return best


def _from_meta(html):
    for pat in (r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
                r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']'):
        m = re.search(pat, html or "", re.S | re.I)
        if m:
            return html_to_text(m.group(1))
    return ""


def jd_from_url(url, timeout=15):
    """공고 링크에서 본문을 가져온다. -> (텍스트, 오류메시지)

    네 가지 방법을 차례로 시도하고 가장 공고다운 결과를 고릅니다.
      1) JobPosting 구조화 데이터 (가장 깨끗함)
      2) 페이지에 박힌 JSON (__NEXT_DATA__ 등)
      3) HTML 본문
      4) og:description
    그래도 안 되면 붙여넣기로 안내합니다.
    """
    url = (url or "").strip()
    if not url:
        return "", None, {}
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url

    try:
        import requests
    except ImportError:
        return "", "requests 가 설치되지 않았습니다.", {}

    try:
        res = requests.get(url, timeout=timeout, headers=_HEADERS, allow_redirects=True)
    except Exception as exc:
        return "", "페이지를 열지 못했습니다: %s" % type(exc).__name__, {}

    if res.status_code >= 400:
        if res.status_code == 404:
            msg = ("공고를 찾을 수 없습니다 (404). 마감돼 내려간 공고이거나 "
                   "주소가 바뀐 것 같습니다. 내용을 직접 붙여넣어 주세요.")
        else:
            msg = ("사이트가 접근을 막았습니다 (HTTP %d). 로그인이 필요하거나 "
                   "자동 접근을 차단하는 사이트입니다. 내용을 직접 붙여넣어 주세요."
                   % res.status_code)
        return "", msg, {}

    res.encoding = res.apparent_encoding or res.encoding
    html = res.text

    best, how = "", ""
    for name, fn in (("구조화 데이터", _from_jsonld),
                     ("페이지 내 데이터", _from_embedded_json),
                     ("본문", html_to_text),
                     ("페이지 요약", _from_meta)):
        try:
            cand = fn(html)
        except Exception:
            continue
        if _score_jd(cand) > _score_jd(best):
            best, how = cand, name

    best = clean_text(best)
    hints = sum(1 for h in JD_HINTS if h.lower() in best.lower())

    if len(best) < 300 or hints < 2:
        return "", ("공고 본문을 찾지 못했습니다. 화면을 자바스크립트로 그리거나 "
                    "로그인이 필요한 사이트로 보입니다. "
                    "공고 페이지에서 내용을 복사해 붙여넣어 주세요."), {}

    # 메뉴·푸터만 긁어온 '가짜 성공'을 그냥 통과시키면 사용자가 속는다
    thin = len(best) < 900 or hints < 3
    return best, None, {"how": how, "chars": len(best), "hints": hints, "thin": thin}


def html_to_text(html):
    """HTML 에서 본문으로 보이는 글자만 남긴다."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return re.sub(r"<[^>]+>", " ", html or "")

    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(_DROP_TAGS):
        tag.decompose()

    # 글자가 가장 많이 몰려 있는 덩어리를 본문으로 본다
    best, best_len = None, 0
    for node in soup.find_all(["main", "article", "section", "div"]):
        length = len(node.get_text(" ", strip=True))
        if length > best_len:
            best, best_len = node, length
    root = best if best_len > 400 else soup

    text = root.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [l.strip() for l in text.split("\n")]
    return "\n".join(l for l in lines if l)


def clean_text(text):
    """줄바꿈·공백 정리. 파싱 전에 한 번 통과시킵니다."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace(" ", " ").replace("​", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(l.strip() for l in text.split("\n")).strip()
