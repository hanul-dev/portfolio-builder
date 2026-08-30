# -*- coding: utf-8 -*-
"""미리보기 · 다운로드."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from core import schema, deck, io_utils
from core import render as html_render
from views import common as C


def render():
    if C.locked():
        return
    d = C.doc()
    t = C.target()
    C.page_head("미리보기 · 다운로드",
                "지금 설정 그대로 웹페이지와 발표자료를 만듭니다. 원본 이력은 바뀌지 않습니다.")

    b = d["base"]
    if not b["person"].get("name") and not b["projects"]:
        C.empty_hint("아직 내용이 없습니다. **내 정보** 탭부터 채워 주세요.")
        return

    view = schema.build_view(d, t)
    stem = schema.file_stem(d, t)

    c1, c2, c3 = st.columns(3)
    with c1:
        html = html_render.render_html(view)
        st.download_button("🌐 웹페이지 (HTML)", html, file_name=stem + ".html",
                           mime="text/html", use_container_width=True, type="primary",
                           help="이미지까지 파일 하나에 들어갑니다. 그대로 메일에 첨부해도 열립니다.")
    with c2:
        if st.button("📊 PPT 만들기", use_container_width=True):
            with st.spinner("슬라이드를 만드는 중..."):
                try:
                    st.session_state.pptx = deck.build(view).getvalue()
                    st.session_state.pptx_name = stem + ".pptx"
                except Exception as exc:
                    st.session_state.pptx = None
                    st.error("PPT 생성에 실패했습니다: %s" % exc)
        if st.session_state.get("pptx"):
            st.download_button("⬇ PPTX 내려받기", st.session_state.pptx,
                               file_name=st.session_state.get("pptx_name", stem + ".pptx"),
                               mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                               use_container_width=True)
    with c3:
        st.download_button("💾 데이터 (JSON)", io_utils.doc_to_json(d),
                           file_name=stem + ".json", mime="application/json",
                           use_container_width=True,
                           help="다음에 이어서 작업하려면 이 파일을 보관하세요.")

    n_slides = 3 + len(view["projects"]) + (1 if view["custom"] else 0) \
        + (1 if (view["skills"] or view["languages"]) else 0) \
        + (1 if (view["education"] or view["awards"] or view["activities"]) else 0) + 1
    st.caption("현재 구성 · 프로젝트 %d건 · 예상 슬라이드 %d장 · 수치 표기 %s"
               % (len(view["projects"]), n_slides,
                  "숨김" if t.get("hide_numbers", True) else "표시"))

    st.info("PDF 로 내야 한다면 HTML 을 내려받아 브라우저에서 열고 `Ctrl+P` → 대상을 "
            "**PDF로 저장** 으로 지정하세요. 인쇄용 스타일이 적용되어 있습니다.", icon=":material/print:")

    st.divider()
    st.markdown("#### 미리보기")
    height = st.select_slider("미리보기 높이", [600, 900, 1200, 1800], value=900,
                              key=C.k("previewh"))
    components.html(html, height=height, scrolling=True)


