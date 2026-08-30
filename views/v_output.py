# -*- coding: utf-8 -*-
"""미리보기 · 다운로드."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from core import schema, deck
from core import render as html_render
from views import common as C


def render():
    if C.locked():
        return
    d = C.doc()
    t = C.target()
    C.page_head("미리보기 · 다운로드",
                "지금 설정 그대로 웹페이지와 발표자료를 만듭니다. 원본 이력은 바뀌지 않습니다.",
                eyebrow="Export")

    b = d["base"]
    if not b["person"].get("name") and not b["projects"]:
        C.empty_hint("아직 내용이 없습니다. **내 정보** 탭부터 채워 주세요.")
        return

    view = schema.build_view(d, t)
    stem = schema.file_stem(d, t)

    html = html_render.render_html(view)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("PDF로 저장", html_render.render_html(view, auto_print=True),
                           file_name=stem + "_PDF저장.html", mime="text/html",
                           icon=":material/picture_as_pdf:",
                           use_container_width=True, type="primary",
                           help="받은 파일을 열면 인쇄 창이 바로 뜹니다. "
                                "대상을 'PDF로 저장'으로 고르면 끝입니다.")
        st.caption("**지원서 제출용.** 파일을 열면 인쇄 창이 바로 뜹니다.")
    with c2:
        st.download_button("웹페이지", html, file_name=stem + ".html",
                           mime="text/html", icon=":material/language:",
                           use_container_width=True,
                           help="사진까지 파일 하나에 들어갑니다. 메일에 첨부해도 그대로 열립니다.")
        st.caption("**링크·메일용.** 파일 하나로 열립니다.")
    with c3:
        if st.button("발표자료 만들기", use_container_width=True,
                     icon=":material/slideshow:"):
            with st.spinner("슬라이드를 만드는 중..."):
                try:
                    st.session_state.pptx = deck.build(view).getvalue()
                    st.session_state.pptx_name = stem + ".pptx"
                except Exception as exc:
                    st.session_state.pptx = None
                    st.error("발표자료를 만들지 못했습니다: %s" % exc)
        if st.session_state.get("pptx"):
            st.download_button("PPT 내려받기", st.session_state.pptx,
                               file_name=st.session_state.get("pptx_name", stem + ".pptx"),
                               mime="application/vnd.openxmlformats-officedocument."
                                    "presentationml.presentation",
                               icon=":material/download:", use_container_width=True)
        else:
            st.caption("**면접 발표용.** PowerPoint 로 고칠 수 있습니다.")

    n_slides = 3 + len(view["projects"]) + (1 if view["custom"] else 0) \
        + (1 if (view["skills"] or view["languages"]) else 0) \
        + (1 if (view["education"] or view["awards"] or view["activities"]) else 0) + 1
    st.caption("현재 구성 · 프로젝트 %d건 · 예상 슬라이드 %d장 · 수치 표기 %s"
               % (len(view["projects"]), n_slides,
                  "숨김" if t.get("hide_numbers", True) else "표시"))

    with st.expander("PDF 가 잘 안 만들어지나요?"):
        st.markdown("""
받은 파일을 열었는데 인쇄 창이 안 뜬다면, 그 화면에서 `Ctrl+P` (Mac 은 `⌘+P`) 를 누르세요.

- **대상 · 프린터** 를 **PDF로 저장** 으로 바꿉니다.
- 배경색이 빠져 나오면 **추가 설정 → 배경 그래픽** 을 켜세요.
- 여백은 **기본** 이 가장 보기 좋습니다.

Chrome · Edge · Safari 모두 같은 방식입니다.
""")

    st.divider()
    st.caption("작업 중인 내용을 백업하려면 사이드바의 **작업 내용 백업** 을 쓰세요. "
               "제출용 파일이 아니라, 나중에 이어서 작업할 때 올리는 파일입니다.")

    st.divider()
    st.markdown("#### 미리보기")
    height = st.select_slider("미리보기 높이", [600, 900, 1200, 1800], value=900,
                              key=C.k("previewh"))
    components.html(html, height=height, scrolling=True)


