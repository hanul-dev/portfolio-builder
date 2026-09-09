# -*- coding: utf-8 -*-
"""결과물 내려받기 블록.

'자동 만들기' 끝과 '미리보기 · 다운로드' 두 곳에서 같이 씁니다.
이력서를 올린 자리에서 바로 파일을 받을 수 있어야 하기 때문입니다.

만든 파일은 지금 내용의 지문(sig)과 함께 보관합니다. 내용을 고치면
지문이 달라져 예전 파일이 그대로 내려가는 일이 없습니다.
"""

from __future__ import annotations

import hashlib
import json

import streamlit as st

from core import schema, deck, pdf
from core import render as html_render
from views import common as C

# (키, 라벨, 설명, 확장자, MIME)
KINDS = [
    ("pdf", "PDF", "지원서 제출용 · 그대로 첨부하면 됩니다", "pdf",
     "application/pdf"),
    ("pptx", "발표자료 (PPT)", "면접 발표용 · PowerPoint 로 고칠 수 있습니다", "pptx",
     "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    ("html", "웹페이지", "링크·메일용 · 사진까지 파일 하나에 들어갑니다", "html",
     "text/html"),
]
DEFAULT_ON = {"pdf": True, "pptx": True, "html": False}


def _sig(view):
    """지금 내용의 지문. 내용이 바뀌면 만들어 둔 파일을 버린다."""
    raw = json.dumps(view, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _make(kind, view):
    """(바이트, 경고문). 경고문은 만들긴 했지만 알려야 할 게 있을 때."""
    if kind == "pdf":
        try:
            return pdf.build(view).getvalue(), ""
        except pdf.FontMissing:
            # 글꼴이 없으면 네모만 찍힌 PDF 대신, 열면 인쇄창이 뜨는 파일을 준다
            return (html_render.render_html(view, auto_print=True).encode("utf-8"),
                    "이 서버에 한글 글꼴이 없어 PDF 대신 **인쇄용 파일**을 만들었습니다. "
                    "열면 인쇄 창이 바로 뜨고, 대상을 'PDF로 저장'으로 고르면 됩니다.")
    if kind == "pptx":
        return deck.build(view).getvalue(), ""
    return html_render.render_html(view).encode("utf-8"), ""


def _ext(kind, warn):
    """PDF 를 못 만들어 인쇄용으로 대체했으면 확장자도 바꿔야 한다."""
    if kind == "pdf" and warn:
        return "html", "text/html"
    for k, _label, _desc, ext, mime in KINDS:
        if k == kind:
            return ext, mime
    return "bin", "application/octet-stream"


def download_block(prefix="out", heading=True):
    """고를 수 있는 내려받기 블록을 그린다."""
    d = C.doc()
    t = C.target()
    b = d["base"]
    if not b["person"].get("name") and not b["projects"] and not b["experience"]:
        C.empty_hint("먼저 이력서를 올리거나 **내 정보** 를 채워 주세요. "
                     "내용이 있어야 파일을 만들 수 있습니다.")
        return

    view = schema.build_view(d, t)
    stem = schema.file_stem(d, t)
    sig = _sig(view)

    if heading:
        st.markdown("#### 어떤 파일이 필요하세요?")
        st.caption("필요한 것만 고르고 한 번에 만드세요. 원본 이력은 바뀌지 않습니다.")

    cols = st.columns(len(KINDS))
    picked = []
    for col, (kind, label, desc, _ext_, _mime) in zip(cols, KINDS):
        with col:
            on = st.checkbox(label, value=DEFAULT_ON.get(kind, False),
                             key="%s_pick_%s" % (prefix, kind))
            st.caption(desc)
            if on:
                picked.append(kind)

    if st.button("선택한 파일 만들기", type="primary", use_container_width=True,
                 icon=":material/auto_awesome:", key="%s_build" % prefix,
                 disabled=not picked):
        made = {}
        errors = []
        with st.spinner("파일을 만드는 중..."):
            for kind in picked:
                try:
                    data, warn = _make(kind, view)
                    made[kind] = {"data": data, "warn": warn}
                except Exception as exc:
                    label = dict((k, l) for k, l, _d, _e, _m in KINDS)[kind]
                    errors.append("%s: %s" % (label, exc))
        # 지문 하나만 남긴다. 내용을 고치면 예전 파일이 그대로 내려가면 안 된다.
        st.session_state.built_files = {sig: made}
        st.session_state["%s_errors" % prefix] = errors

    made = st.session_state.get("built_files", {}).get(sig)
    errors = st.session_state.get("%s_errors" % prefix) or []
    for e in errors:
        st.error("만들지 못했습니다 · %s" % e, icon=":material/error:")

    if not made:
        if st.session_state.get("built_files"):
            st.caption("내용이 바뀌었습니다. **선택한 파일 만들기** 를 다시 눌러 주세요.")
        return

    st.success("파일을 만들었습니다. 아래에서 내려받으세요.",
               icon=":material/check_circle:")
    cols = st.columns(len(made))
    for col, (kind, item) in zip(cols, made.items()):
        label = dict((k, l) for k, l, _d, _e, _m in KINDS)[kind]
        ext, mime = _ext(kind, item["warn"])
        with col:
            st.download_button("%s 내려받기" % label, item["data"],
                               file_name="%s.%s" % (stem, ext), mime=mime,
                               icon=":material/download:",
                               use_container_width=True,
                               key="%s_dl_%s" % (prefix, kind))
    for item in made.values():
        if item["warn"]:
            st.warning(item["warn"], icon=":material/info:")
