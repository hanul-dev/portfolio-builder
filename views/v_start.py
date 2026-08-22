# -*- coding: utf-8 -*-
"""시작하기 · 문서 불러오기 / 저장 / 현황."""

from __future__ import annotations

import os

import streamlit as st

from core import schema, io_utils
from views import common as C


def _is_blank(d):
    b = d["base"]
    return (not b["person"].get("name") and not b["projects"] and not b["experience"])


def render():
    d = C.doc()
    C.page_head("시작하기", "내 이력을 한 번 입력해 두면, 지원하는 회사마다 순서와 문장만 바꿔 쓸 수 있습니다.")

    if st.session_state.get("loaded_from") == "local":
        st.warning(
            "이 컴퓨터의 `app/data/my_portfolio.json` 을 불러왔습니다. "
            "개인 정보가 담긴 파일이니, 앱을 인터넷에 배포할 때는 이 파일을 반드시 제외하세요.",
            icon=":material/lock:")

    # ---------------- 불러오기 ----------------
    st.markdown("#### 데이터 불러오기")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**JSON 불러오기**")
        st.caption("전에 내보낸 파일을 올리면 이어서 작업합니다.")
        up = st.file_uploader("JSON 파일", type=["json"], key=C.k("upload"),
                              label_visibility="collapsed")
        if up is not None:
            newdoc, err = io_utils.json_to_doc(up.read())
            if err:
                st.error(err)
            else:
                st.session_state.doc = newdoc
                st.session_state.loaded_from = "upload"
                C.bump()
                st.success("불러왔습니다.")
                st.rerun()

    with c2:
        st.markdown("**예시로 둘러보기**")
        st.caption("가상 인물의 데이터로 기능을 먼저 확인해 보세요.")
        if st.button("예시 데이터 불러오기", use_container_width=True):
            demo = io_utils.load_file(io_utils.DEMO_PATH)
            if demo:
                st.session_state.doc = demo
                st.session_state.loaded_from = "demo"
                C.bump()
                st.rerun()
            else:
                st.error("예시 파일을 찾을 수 없습니다.")

    with c3:
        st.markdown("**처음부터 만들기**")
        st.caption("빈 문서로 시작합니다. 지금 내용은 지워집니다.")
        if st.button("빈 문서로 시작", use_container_width=True):
            st.session_state.doc = schema.empty_doc()
            st.session_state.loaded_from = "new"
            C.bump()
            st.rerun()

    st.divider()

    # ---------------- 현황 ----------------
    if _is_blank(d):
        C.empty_hint("아직 비어 있습니다. **내 정보** 탭에서 이름과 연락처부터 채워 보세요. "
                     "무엇을 적어야 할지 모르겠다면 위에서 예시 데이터를 불러와 구조를 먼저 보세요.")
    else:
        b = d["base"]
        st.markdown("#### 현재 상태")
        cols = st.columns(5)
        stats = [
            ("경력", len(b["experience"])),
            ("프로젝트", len(b["projects"])),
            ("보유 역량", len(b["skills"])),
            ("자격 · 수상", len(b["certificates"]) + len(b["awards"])),
            ("지원처", len(d["targets"])),
        ]
        for col, (label, n) in zip(cols, stats):
            col.metric(label, "%d건" % n)

        t = C.target()
        done = []
        todo = []
        (done if b["person"].get("name") else todo).append("기본 정보")
        (done if b["person"].get("photo") else todo).append("증명사진")
        (done if b["projects"] else todo).append("프로젝트")
        (done if t.get("jd_text") else todo).append("공고문 입력")
        (done if t.get("hero_title") else todo).append("첫인상 문구")
        (done if t.get("intro") else todo).append("자기소개")
        if todo:
            st.caption("아직 안 채운 항목: " + " · ".join(todo))
        else:
            st.caption("필요한 항목을 모두 채웠습니다. **미리보기 · 다운로드** 탭에서 결과물을 받아 가세요.")

    st.divider()

    # ---------------- 저장 ----------------
    st.markdown("#### 저장")
    st.caption("Streamlit 은 브라우저를 닫으면 작업 내용이 사라집니다. "
               "JSON 으로 내려받아 두면 다음에 그대로 이어서 쓸 수 있습니다.")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("JSON 파일로 내려받기", io_utils.doc_to_json(d),
                           file_name=schema.file_stem(d) + ".json",
                           mime="application/json", use_container_width=True, type="primary")
    with c2:
        if io_utils.is_local_mode():
            can_write = os.access(os.path.dirname(io_utils.LOCAL_PATH) or ".", os.W_OK)
            if st.button("이 컴퓨터에 저장", use_container_width=True, disabled=not can_write,
                         help="app/data/my_portfolio.json 에 저장하고, 다음 실행 때 자동으로 "
                              "불러옵니다. 내 PC 에서 혼자 쓸 때만 쓰는 기능입니다."):
                try:
                    io_utils.save_file(d, io_utils.LOCAL_PATH)
                    st.session_state.dirty = False
                    st.success("저장했습니다: app/data/my_portfolio.json")
                except Exception as exc:
                    st.error("저장하지 못했습니다: %s" % exc)
        else:
            st.button("이 컴퓨터에 저장", use_container_width=True, disabled=True,
                      help="여러 사람이 함께 쓰는 주소에서는 꺼져 있습니다. "
                           "서버에 저장하면 다음 접속자에게 내 이력이 보이기 때문입니다.")
            st.caption("공유 주소에서는 서버 저장이 막혀 있습니다. JSON 으로 내려받아 보관하세요.")

    with st.expander("이 앱은 어떻게 쓰나요?"):
        st.markdown("""
1. **내 정보** · **경력 · 프로젝트** 에 내 이력을 한 번만 입력합니다. 여기 있는 내용이 원본이고, 지원처를 아무리 늘려도 훼손되지 않습니다.
2. **공고 분석** 에서 지원할 회사와 공고문을 붙여넣습니다. 공고 문장에서 요구 역량을 뽑아 내 이력과 대조합니다.
3. **추천 수정안** 에서 헤드라인 · 자기소개 · 프로젝트 순서 제안을 확인하고 원하는 것만 적용합니다. 문장은 **내가 입력한 내용으로** 만들어지므로, 없는 경력이 지어내지지 않습니다.
4. **미리보기 · 다운로드** 에서 웹페이지(HTML) 와 발표자료(PPTX) 를 받아 갑니다.

지원처를 새로 만들면 1번의 이력은 그대로 두고 3번의 구성만 다시 잡으면 됩니다.
""")
