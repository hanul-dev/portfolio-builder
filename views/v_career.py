# -*- coding: utf-8 -*-
"""경력 · 프로젝트 편집."""

from __future__ import annotations

import streamlit as st

from core import schema
from views import common as C


def _experience_tab(b):
    st.caption("회사 단위로 적습니다. 개별 성과는 아래 프로젝트 탭에 나눠 쓰는 편이 읽기 좋습니다.")
    for i, ex in enumerate(list(b["experience"])):
        title = " · ".join(y for y in [ex.get("org", ""), ex.get("role", "")] if y) or "(새 경력)"
        with st.expander(title, expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                C.text_field("회사", ex, "org", wid=C.k("ex", i, "org"))
                C.text_field("기간", ex, "period", wid=C.k("ex", i, "period"),
                             placeholder="2024.09 - 재직중")
            with c2:
                C.text_field("직무", ex, "role", wid=C.k("ex", i, "role"))
                c3, c4 = st.columns(2)
                with c3:
                    C.text_field("고용 형태", ex, "type", wid=C.k("ex", i, "type"),
                                 placeholder="정규직 / 인턴")
                with c4:
                    C.text_field("재직 기간", ex, "duration", wid=C.k("ex", i, "duration"),
                                 placeholder="1년 8개월")
            C.area_field("요약", ex, "summary", height=120, wid=C.k("ex", i, "summary"),
                         placeholder="무엇을 담당했고 어떤 결과를 만들었는지 3~4문장으로.")
            C.lines_field("주요 성과 (한 줄에 하나)", ex, "points", height=100)
            C.tag_field(ex, help="이 경력이 충족하는 요구사항을 고르면 공고 매칭도에 반영됩니다.")
            st.divider()
            C.move_buttons(b["experience"], i, "exp")

    if st.button("+ 경력 추가", key=C.k("expadd"), type="primary"):
        b["experience"].append(schema.empty_experience())
        C.dirty()
        C.bump()
        st.rerun()


def _project_tab(b):
    st.caption("배경 → 실행 → 성과 순서로 적으면 현업이 읽는 흐름과 같아집니다. "
               "3~5건이 가장 읽기 좋습니다.")

    for i, pr in enumerate(list(b["projects"])):
        title = pr.get("title") or "(새 프로젝트)"
        with st.expander("%02d. %s" % (i + 1, title), expanded=False):
            c1, c2 = st.columns([3, 2])
            with c1:
                C.text_field("제목", pr, "title", wid=C.k("pr", i, "title"))
                C.text_field("한 줄 요약", pr, "subtitle", wid=C.k("pr", i, "subtitle"),
                             placeholder="이 프로젝트를 한 문장으로")
            with c2:
                C.text_field("소속 · 클라이언트", pr, "org", wid=C.k("pr", i, "org"))
                cc1, cc2 = st.columns(2)
                with cc1:
                    C.text_field("기간", pr, "period", wid=C.k("pr", i, "period"))
                with cc2:
                    C.text_field("내 역할", pr, "my_role", wid=C.k("pr", i, "my_role"))

            st.markdown("**대표 지표**")
            cc1, cc2 = st.columns(2)
            with cc1:
                C.text_field("숫자", pr, "metric_value", wid=C.k("pr", i, "mv"),
                             placeholder="-37%")
            with cc2:
                C.text_field("라벨", pr, "metric_label", wid=C.k("pr", i, "ml"),
                             placeholder="CPI 개선")

            C.area_field("배경 (BACKGROUND)", pr, "background", height=110,
                         wid=C.k("pr", i, "bg"),
                         placeholder="어떤 문제가 있었고, 왜 이 일이 필요했는지.")
            C.lines_field("실행 (ACTION · 한 줄에 하나)", pr, "actions", height=140,
                          placeholder="내가 직접 한 일을 순서대로")
            C.area_field("성과 (RESULT)", pr, "result", height=100, wid=C.k("pr", i, "rs"),
                         placeholder="무엇이 어떻게 달라졌는지.")
            C.lines_field("핵심 역량 (한 줄에 하나)", pr, "core_skills", height=90)
            C.tag_field(pr)

            with st.expander("🔒 수치 숨김용 문장 (선택)"):
                st.caption("광고주 성과처럼 대외비일 수 있는 숫자는 여기에 '숫자 없는 표현'을 같이 적어 두면, "
                           "지원처별로 숫자를 빼고 내보낼 수 있습니다. 비워 두면 원문이 그대로 쓰입니다.")
                C.text_field("한 줄 요약 (숫자 없이)", pr, "subtitle_safe", wid=C.k("pr", i, "sts"),
                             placeholder="CPI 개선, 목표 KPI 첫 초과 달성")
                cc1, cc2 = st.columns(2)
                with cc1:
                    C.text_field("지표 숫자 (숫자 없이)", pr, "metric_value_safe",
                                 wid=C.k("pr", i, "mvs"), placeholder="초과 달성")
                with cc2:
                    C.text_field("지표 라벨 (숫자 없이)", pr, "metric_label_safe",
                                 wid=C.k("pr", i, "mls"), placeholder="목표 KPI")
                C.area_field("성과 (숫자 없이)", pr, "result_safe", height=90,
                             wid=C.k("pr", i, "rss"))

            st.markdown("**기획 자료 이미지**")
            C.image_field("이미지 올리기", pr, "image",
                          help="기획서 슬라이드나 결과 화면 캡처. 가로형이 잘 맞습니다.")

            st.divider()
            C.move_buttons(b["projects"], i, "proj")

    if st.button("+ 프로젝트 추가", key=C.k("projadd"), type="primary"):
        b["projects"].append(schema.empty_project())
        C.dirty()
        C.bump()
        st.rerun()


def render():
    d = C.doc()
    b = d["base"]
    C.page_head("경력 · 프로젝트", "지원처별 순서와 노출은 나중에 정합니다. 여기서는 사실만 모아 두세요.")

    tab1, tab2 = st.tabs(["프로젝트 (%d)" % len(b["projects"]),
                          "경력 (%d)" % len(b["experience"])])
    with tab1:
        _project_tab(b)
    with tab2:
        _experience_tab(b)
