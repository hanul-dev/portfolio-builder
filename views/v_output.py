# -*- coding: utf-8 -*-
"""미리보기 · 다운로드."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from core import schema
from core import render as html_render
from views import common as C
from views import exports


def render():
    if C.locked():
        return
    d = C.doc()
    t = C.target()
    C.page_head("미리보기 · 다운로드",
                "지금 설정 그대로 PDF · 발표자료 · 웹페이지를 만듭니다. "
                "원본 이력은 바뀌지 않습니다.",
                eyebrow="Export")

    b = d["base"]
    if not b["person"].get("name") and not b["projects"]:
        C.empty_hint("아직 내용이 없습니다. **내 정보** 탭부터 채워 주세요.")
        return

    view = schema.build_view(d, t)

    exports.download_block(prefix="output")

    n_slides = 3 + len(view["projects"]) + (1 if view["custom"] else 0) \
        + (1 if (view["skills"] or view["languages"]) else 0) \
        + (1 if (view["education"] or view["awards"] or view["activities"]) else 0) + 1
    st.caption("현재 구성 · 프로젝트 %d건 · 예상 슬라이드 %d장 · 수치 표기 %s"
               % (len(view["projects"]), n_slides,
                  "숨김" if t.get("hide_numbers", True) else "표시"))

    st.divider()
    st.caption("작업 중인 내용을 백업하려면 사이드바의 **작업 내용 백업** 을 쓰세요. "
               "제출용 파일이 아니라, 나중에 이어서 작업할 때 올리는 파일입니다.")

    st.divider()
    html = html_render.render_html(view)
    st.markdown("#### 미리보기")
    height = st.select_slider("미리보기 높이", [600, 900, 1200, 1800], value=900,
                              key=C.k("previewh"))
    components.html(html, height=height, scrolling=True)


