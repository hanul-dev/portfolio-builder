# -*- coding: utf-8 -*-
"""취준 포폴 뽀개기 · 공고에 맞춰 다시 쓰는 포트폴리오 · Streamlit 앱.

    streamlit run app/app.py
"""

from __future__ import annotations

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import schema, io_utils, browser_store, auth   # noqa: E402
from views import common as C                # noqa: E402
from views import (v_auto, v_start, v_basics, v_career,  # noqa: E402
                   v_target, v_tailor, v_output)

from views.style import BRAND, BRAND_MARK, BRAND_SUB   # noqa: E402

st.set_page_config(page_title=BRAND, page_icon="📄",
                   layout="wide", initial_sidebar_state="expanded")

from views.style import CSS   # noqa: E402

st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------- 최초 로딩
def boot():
    if "doc" in st.session_state:
        return
    st.session_state.nonce = 0
    st.session_state.dirty = False
    st.session_state.loaded_from = None
    st.session_state.autosave = True

    # 내 PC 에서 혼자 쓸 때만 서버 파일을 읽는다.
    # 여러 사람이 쓰는 주소에서는 남의 이력이 보이면 안 되므로 건너뛴다.
    local = io_utils.load_file(io_utils.LOCAL_PATH) if io_utils.is_local_mode() else None
    if local:
        st.session_state.doc = local
        st.session_state.loaded_from = "local"
    else:
        st.session_state.doc = schema.empty_doc()


def restore_from_browser():
    """브라우저에 저장해 둔 내용을 되살린다.

    컴포넌트가 값을 늦게 넘겨주기도 해서, 아직 아무것도 안 만진 상태라면
    여러 번에 걸쳐 다시 시도한다.
    """
    if st.session_state.get("browser_restored") or st.session_state.get("loaded_from"):
        return
    d = st.session_state.doc
    untouched = not (d["base"]["projects"] or d["base"]["experience"]
                     or d["base"]["person"].get("name") or st.session_state.get("dirty"))
    if not untouched:
        st.session_state.browser_restored = True     # 이미 작업 중이면 덮지 않는다
        return

    doc, err = browser_store.restore()
    if err:
        st.session_state.browser_restore_error = err
        st.session_state.browser_restored = True
        return
    if doc:
        st.session_state.doc = doc
        st.session_state.loaded_from = "browser"
        st.session_state.browser_restored = True
        C.bump()
        st.rerun()


boot()
if auth.passed():
    # 비밀번호를 통과하기 전에는 저장된 내용을 불러오지 않는다
    restore_from_browser()


# ---------------------------------------------------------------- 사이드바
def sidebar():
    d = st.session_state.doc
    with st.sidebar:
        name = d["base"]["person"].get("name") or "이름 없음"
        st.markdown(
            "<div class='brand'><div class='brand-mark'>%s</div>"
            "<div><div class='brand-name'>%s</div>"
            "<div class='brand-sub'>%s</div></div></div>"
            % (BRAND_MARK, BRAND, BRAND_SUB),
            unsafe_allow_html=True)
        st.markdown(
            "<div class='who'><b>%s</b><span>프로젝트 %d건 · 지원처 %d곳</span></div>"
            % (name, len(d["base"]["projects"]), len(d["targets"])),
            unsafe_allow_html=True)
        st.write("")

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
        st.download_button("작업 내용 백업", io_utils.doc_to_json(d),
                           file_name=stem + "_작업파일.json",
                           mime="application/json", icon=":material/backup:",
                           use_container_width=True,
                           help="지금까지 입력한 내용을 파일 하나로 내려받습니다. "
                                "다른 컴퓨터에서 이어서 작업할 때 이 파일을 올리면 "
                                "그대로 복구됩니다. 완성본이 아니라 '작업 중인 원고'입니다.")
        st.caption("완성본(PDF · PPT)은 **미리보기 · 다운로드** 에서 받습니다.")

        st.divider()
        _autosave_box(d)
        auth.logout_button()


def _autosave_box(d):
    """자동 저장 상태. 저장은 이 사람 브라우저 안에서만 일어난다."""
    if not browser_store.available():
        st.caption("이 브라우저에서는 자동 저장을 쓸 수 없습니다. "
                   "위의 **작업 내용 백업** 으로 내려받아 두세요.")
        return

    on = st.checkbox("이 브라우저에 자동 저장", value=st.session_state.get("autosave", True),
                     help="작업 내용을 이 브라우저에만 저장합니다. 서버에는 남지 않고, "
                          "다른 사람에게도 보이지 않습니다.")
    st.session_state.autosave = on

    if browser_store.too_big(d):
        st.caption("⚠️ 내용이 커서(%.1fMB) 자동 저장을 건너뜁니다. 작업 내용을 백업해 두세요."
                   % (browser_store.payload_size(d) / 1_000_000))
        return

    if on:
        if browser_store.autosave(d):
            st.caption("✅ 저장됨")
        elif browser_store.changed_since_save(d):
            st.caption("저장 중…")
        else:
            st.caption("✅ 저장됨")
    elif st.session_state.get("dirty"):
        st.caption("⚠️ 저장하지 않은 변경이 있습니다")


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
nav.run()                    # 본문 (잠겨 있으면 각 화면이 잠금 화면을 그린다)
if auth.passed():
    sidebar()                # 통과한 뒤에만 사이드바 내용을 그린다
