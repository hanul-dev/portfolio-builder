# -*- coding: utf-8 -*-
"""내 정보 · 기본 인적사항, 학력, 어학, 역량, 자격, 수상, 활동, 자유 섹션."""

from __future__ import annotations

import streamlit as st

from views import common as C


def render():
    d = C.doc()
    b = d["base"]
    C.page_head("내 정보", "여기 입력한 내용이 모든 지원처에서 공유되는 원본입니다.")

    tabs = st.tabs(["기본 정보", "학력 · 어학", "역량 · 자격", "수상 · 활동", "자유 섹션"])

    # ---------------- 기본 정보 ----------------
    with tabs[0]:
        p = b["person"]
        c1, c2 = st.columns([2, 1])
        with c1:
            a, bb = st.columns(2)
            with a:
                C.text_field("이름", p, "name", placeholder="홍길동")
                C.text_field("생년월일", p, "birth", placeholder="1996.03.21")
                C.text_field("연락처", p, "phone", placeholder="010-0000-0000")
            with bb:
                C.text_field("영문 이름", p, "name_en", placeholder="Hong Gildong")
                C.text_field("희망 직무", p, "job_title", placeholder="마케팅 / 서비스 기획 등")
                C.text_field("이메일", p, "email", placeholder="me@example.com")
            C.text_field("거주지", p, "location", placeholder="서울 마포구")
        with c2:
            st.markdown("**증명사진**")
            C.image_field("사진 올리기", p, "photo",
                          help="세로형(3:4) 사진이 가장 잘 맞습니다. 자동으로 크기를 줄여 저장합니다.")

        st.divider()
        st.markdown("**외부 링크**")
        st.caption("노션 포트폴리오, 블로그, GitHub 등. 표지와 연락처 영역에 함께 나옵니다.")
        links = p.setdefault("links", [])
        for i, link in enumerate(list(links)):
            c1, c2, c3 = st.columns([1, 3, 1])
            with c1:
                C.text_field("이름", link, "label", wid=C.k("lk", i, "label"))
            with c2:
                C.text_field("URL", link, "url", wid=C.k("lk", i, "url"))
            with c3:
                st.write("")
                st.write("")
                if st.button("삭제", key=C.k("lkdel", i), use_container_width=True):
                    links.pop(i)
                    C.dirty()
                    C.bump()
                    st.rerun()
        if st.button("+ 링크 추가", key=C.k("lkadd")):
            links.append({"label": "", "url": ""})
            C.bump()
            st.rerun()

    # ---------------- 학력 · 어학 ----------------
    with tabs[1]:
        st.markdown("**학력**")
        C.simple_list_editor(
            b["education"],
            {"school": "학교", "dept": "전공", "period": "기간", "note": "비고"},
            "edu", {"school": "", "dept": "", "period": "", "note": ""},
            lambda x: " · ".join(y for y in [x.get("school", ""), x.get("dept", "")] if y),
            "+ 학력 추가")

        st.divider()
        st.markdown("**어학**")
        st.caption("막대 비율은 화면·PPT 의 그래프 길이로 쓰입니다.")
        C.simple_list_editor(
            b["languages"],
            {"name": "언어", "level": "수준", "cert": "성적 · 자격", "date": "취득일", "bar": "막대 비율"},
            "lang", {"name": "", "level": "", "cert": "", "date": "", "bar": 80},
            lambda x: " · ".join(y for y in [x.get("name", ""), x.get("cert", "")] if y),
            "+ 어학 추가")

    # ---------------- 역량 · 자격 ----------------
    with tabs[2]:
        st.markdown("**보유 역량 · 툴**")
        for i, sk in enumerate(list(b["skills"])):
            with st.expander(sk.get("name") or "(이름 없음)"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    C.text_field("항목", sk, "name", placeholder="Google Analytics · 매체 어드민")
                with c2:
                    val = st.slider("숙련도", 0, 100, int(sk.get("bar") or 80), 5,
                                    key=C.k("skbar", i))
                    if val != sk.get("bar"):
                        sk["bar"] = val
                        C.dirty()
                C.tag_field(sk, help="이 역량이 어떤 요구사항을 충족하는지 고르면 공고 매칭에 반영됩니다.")
                st.divider()
                C.move_buttons(b["skills"], i, "sk")
        if st.button("+ 역량 추가", key=C.k("skadd")):
            b["skills"].append({"name": "", "bar": 80, "tags": []})
            C.bump()
            st.rerun()

        st.divider()
        st.markdown("**자격증**")
        for i, ct in enumerate(list(b["certificates"])):
            with st.expander(ct.get("name") or "(이름 없음)"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    C.text_field("자격명", ct, "name")
                with c2:
                    C.text_field("발급 기관", ct, "org")
                with c3:
                    C.text_field("취득일", ct, "date")
                C.tag_field(ct)
                st.divider()
                C.move_buttons(b["certificates"], i, "ct")
        if st.button("+ 자격증 추가", key=C.k("ctadd")):
            b["certificates"].append({"name": "", "org": "", "date": "", "tags": []})
            C.bump()
            st.rerun()

    # ---------------- 수상 · 활동 ----------------
    with tabs[3]:
        st.markdown("**수상**")
        for i, aw in enumerate(list(b["awards"])):
            with st.expander(aw.get("name") or "(이름 없음)"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    C.text_field("수상명", aw, "name")
                with c2:
                    C.text_field("등급", aw, "prize", placeholder="최우수상")
                with c3:
                    C.text_field("일자", aw, "date")
                C.tag_field(aw)
                st.divider()
                C.move_buttons(b["awards"], i, "aw")
        if st.button("+ 수상 추가", key=C.k("awadd")):
            b["awards"].append({"name": "", "prize": "", "date": "", "tags": []})
            C.bump()
            st.rerun()

        st.divider()
        st.markdown("**대외활동 · 봉사**")
        for i, ac in enumerate(list(b["activities"])):
            with st.expander(ac.get("name") or "(이름 없음)"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    C.text_field("활동명", ac, "name")
                with c2:
                    C.text_field("기간", ac, "period")
                with c3:
                    C.text_field("구분", ac, "type", placeholder="대외활동 / 교내활동")
                C.area_field("설명", ac, "desc", height=100)
                C.tag_field(ac)
                st.divider()
                C.move_buttons(b["activities"], i, "ac")
        if st.button("+ 활동 추가", key=C.k("acadd")):
            b["activities"].append({"name": "", "period": "", "type": "", "desc": "", "tags": []})
            C.bump()
            st.rerun()

    # ---------------- 자유 섹션 ----------------
    with tabs[4]:
        cu = b["custom"]
        st.caption("직무에 대한 본인만의 관점을 담는 섹션입니다. 게임사라면 '게임 이해도', "
                   "기획 직무라면 '제품을 보는 관점' 처럼 쓰면 됩니다. "
                   "**답변을 적은 항목만** 포트폴리오에 나오고, 전부 비면 섹션 자체가 사라집니다.")
        c1, c2 = st.columns(2)
        with c1:
            C.text_field("섹션 제목", cu, "title", placeholder="게임 이해도")
        with c2:
            C.text_field("섹션 설명", cu, "subtitle",
                         placeholder="유저로서의 경험과 마케터로서의 해석을 함께 정리했습니다.")

        items = cu.setdefault("items", [])
        for i, it in enumerate(list(items)):
            with st.expander(it.get("q") or "(질문 없음)", expanded=not (it.get("a") or "").strip()):
                C.text_field("질문", it, "q", wid=C.k("cuq", i))
                if it.get("hint"):
                    st.caption("💡 " + it["hint"])
                C.area_field("답변", it, "a", height=160, wid=C.k("cua", i),
                             placeholder="여기는 대신 써 드리지 않습니다. 직접 겪은 내용을 본인 언어로 적으세요.")
                st.divider()
                C.move_buttons(items, i, "cu")
        if st.button("+ 질문 추가", key=C.k("cuadd")):
            items.append({"q": "", "hint": "", "a": ""})
            C.bump()
            st.rerun()

        st.info("이 섹션을 포트폴리오에 노출할지는 **추천 수정안** 탭의 구성 설정에서 지원처별로 켜고 끕니다.",
                icon=":material/info:")
