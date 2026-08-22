# -*- coding: utf-8 -*-
"""지원처 맞춤 포트폴리오 빌더 · Streamlit 앱.

    streamlit run app/app.py
"""

from __future__ import annotations

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import schema, io_utils            # noqa: E402
from views import common as C                # noqa: E402
from views import (v_auto, v_start, v_basics, v_career,  # noqa: E402
                   v_target, v_tailor, v_output)

st.set_page_config(page_title="포트폴리오 빌더", page_icon="📄",
                   layout="wide", initial_sidebar_state="expanded")

CSS = """
<style>
  section.main > div { padding-top: 1.2rem; }
  div[data-testid="stExpander"] details { border-radius: 6px; }
  .stButton button { border-radius: 6px; }
  .pill {
    display:inline-block; padding:3px 10px; margin:2px 4px 2px 0; border-radius:999px;
    font-size:12.5px; border:1px solid #d9dfe5; background:#f4f6f8; color:#2b333c;
  }
  .pill.hit { background:#e6f0f8; border-color:#a8cde5; color:#2c5f8a; font-weight:600; }
  .pill.miss { background:#fdeeee; border-color:#f2c4c4; color:#a33; font-weight:600; }
  .advice { border-left:3px solid #2c5f8a; background:#f4f6f8; padding:10px 14px;
            margin:8px 0; font-size:14px; line-height:1.65; border-radius:0 6px 6px 0; }
  .reco { border:1px solid #d9dfe5; border-radius:8px; padding:14px 16px; margin-bottom:12px; }
  .reco .lb { font-size:11.5px; font-weight:700; letter-spacing:.06em; color:#2c5f8a; }
  .reco .tx { font-size:16px; font-weight:600; margin:6px 0 8px; white-space:pre-line; }
  .reco .wy { font-size:13px; color:#5a656f; line-height:1.6; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------- 최초 로딩
def boot():
    if "doc" in st.session_state:
        return
    st.session_state.nonce = 0
    st.session_state.dirty = False
    st.session_state.loaded_from = None

    # 내 PC 에서 혼자 쓸 때만 저장본을 자동으로 불러온다.
    # 여러 사람이 쓰는 서버에서는 남의 이력이 보이면 안 되므로 건너뛴다.
    local = io_utils.load_file(io_utils.LOCAL_PATH) if io_utils.is_local_mode() else None
    if local:
        st.session_state.doc = local
        st.session_state.loaded_from = "local"
    else:
        st.session_state.doc = schema.empty_doc()


boot()


# ---------------------------------------------------------------- 사이드바
def sidebar():
    d = st.session_state.doc
    with st.sidebar:
        name = d["base"]["person"].get("name") or "이름 없음"
        st.markdown("#### 📄 포트폴리오 빌더")
        st.caption("%s · 프로젝트 %d건" % (name, len(d["base"]["projects"])))
        st.divider()

        ids = list(d["targets"])
        labels = [d["targets"][i].get("label") or i for i in ids]
        idx = ids.index(d["active"]) if d["active"] in ids else 0
        pick = st.selectbox("지원처", range(len(ids)), index=idx,
                            format_func=lambda i: labels[i],
                            help="회사마다 하나씩 만들어 두고 골라 쓰세요. 이력 원본은 공유됩니다.")
        if ids[pick] != d["active"]:
            d["active"] = ids[pick]
            C.bump()
            st.rerun()

        c1, c2 = st.columns(2)
        with c1:
            if st.button("+ 새 지원처", use_container_width=True):
                tid = schema.new_id("t")
                d["targets"][tid] = schema.empty_target("새 지원처")
                d["active"] = tid
                C.dirty()
                C.bump()
                st.rerun()
        with c2:
            if st.button("복제", use_container_width=True,
                         help="지금 지원처의 설정을 그대로 복사합니다"):
                tid = schema.new_id("t")
                copy = schema.clone(schema.active_target(d))
                copy["label"] = (copy.get("label") or "지원처") + " 복사본"
                d["targets"][tid] = copy
                d["active"] = tid
                C.dirty()
                C.bump()
                st.rerun()

        if len(ids) > 1:
            if st.button("현재 지원처 삭제", use_container_width=True):
                del d["targets"][d["active"]]
                d["active"] = list(d["targets"])[0]
                C.dirty()
                C.bump()
                st.rerun()

        st.divider()
        stem = schema.file_stem(d)
        st.download_button("💾 JSON 내보내기", io_utils.doc_to_json(d),
                           file_name=stem + ".json", mime="application/json",
                           use_container_width=True,
                           help="브라우저를 닫으면 작업 내용이 사라집니다. 자주 내려받아 두세요.")
        if st.session_state.get("dirty"):
            st.caption("⚠️ 저장하지 않은 변경이 있습니다")

        st.divider()
        st.caption("입력한 내용은 이 브라우저 세션에만 있고 서버에 저장되지 않습니다. "
                   "JSON 으로 내려받아 보관하세요.")


# ---------------------------------------------------------------- 페이지
pages = [
    st.Page(v_auto.render, title="자동 만들기", icon=":material/bolt:", url_path="auto", default=True),
    st.Page(v_basics.render, title="내 정보", icon=":material/badge:", url_path="basics"),
    st.Page(v_career.render, title="경력 · 프로젝트", icon=":material/work:", url_path="career"),
    st.Page(v_target.render, title="공고 분석", icon=":material/search:", url_path="jd"),
    st.Page(v_tailor.render, title="추천 수정안", icon=":material/auto_fix_high:", url_path="tailor"),
    st.Page(v_output.render, title="미리보기 · 다운로드", icon=":material/download:", url_path="output"),
    st.Page(v_start.render, title="불러오기 · 저장", icon=":material/save:", url_path="save"),
]
nav = st.navigation(pages)   # 사이드바에 메뉴가 먼저 그려진다
nav.run()                    # 본문 (여기서 doc 이 갱신된다)
sidebar()                    # 갱신된 doc 으로 사이드바 요약을 그린다
