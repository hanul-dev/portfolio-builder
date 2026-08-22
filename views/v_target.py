# -*- coding: utf-8 -*-
"""공고 분석 · 지원처 정보 입력과 매칭도 확인."""

from __future__ import annotations

import streamlit as st

from core import reco
from core.tags import tag_label, tag_category
from views import common as C


def _pills(tags, cls):
    if not tags:
        return "<span class='pill'>없음</span>"
    return "".join("<span class='pill %s'>%s</span>" % (cls, tag_label(t)) for t in tags)


def render():
    d = C.doc()
    t = C.target()
    C.page_head("공고 분석", "공고문을 붙여넣으면 요구 역량을 뽑아 내 이력과 대조합니다.")

    c1, c2 = st.columns(2)
    with c1:
        C.text_field("프로필 이름", t, "label", placeholder="○○회사 · 마케팅PM",
                     help="사이드바 목록에 표시되는 이름입니다.")
        C.text_field("지원 회사", t, "company", placeholder="지원하는 회사 이름")
    with c2:
        C.text_field("공고명 · 포지션", t, "position", placeholder="공고에 적힌 포지션명 그대로")
        cc1, cc2 = st.columns(2)
        with cc1:
            C.text_field("마감일", t, "deadline", placeholder="2026-08-16")
        with cc2:
            C.text_field("공고 URL", t, "jd_url", placeholder="https://...")

    C.area_field("공고문 전문", t, "jd_text", height=240,
                 placeholder="담당업무 · 자격요건 · 우대사항을 그대로 붙여넣으세요. "
                             "많이 넣을수록 분석이 정확해집니다.")

    if not (t.get("jd_text") or "").strip():
        C.empty_hint("공고문을 붙여넣으면 여기에 매칭도와 보완 포인트가 나타납니다.")
        return

    st.divider()
    res = reco.analyze(d, t)

    left, right = st.columns([1, 2])
    with left:
        st.metric("공고 충족률", "%d%%" % res["score"],
                  help="공고에서 찾아낸 요구 역량 중, 내 이력 태그로 충족되는 비율입니다.")
        st.progress(res["score"] / 100.0)
        st.caption("요구 역량 %d개 중 %d개 충족" % (len(res["jd_tags"]), len(res["hit"])))
    with right:
        if not res["jd_tags"]:
            st.warning("공고문에서 아는 역량 표현을 찾지 못했습니다. 담당업무·자격요건 문단을 더 붙여넣어 보세요.")
        elif res["score"] >= 80:
            st.success("요구사항 대부분을 이미 갖췄습니다. 남은 건 **순서와 문장**입니다. "
                       "추천 수정안 탭에서 구성을 잡으세요.")
        elif res["score"] >= 50:
            st.info("절반 이상 충족합니다. 아래 미충족 항목 중 실제로 해본 일이 있다면 "
                    "해당 프로젝트에 태그를 추가해 반영하세요.")
        else:
            st.warning("충족률이 낮습니다. 이력을 덜 입력했거나, 직무 방향이 다를 수 있습니다.")

    st.markdown("**충족되는 요구사항**")
    st.markdown(_pills(res["hit"], "hit"), unsafe_allow_html=True)
    st.markdown("**보완이 필요한 요구사항**")
    st.markdown(_pills(res["miss"], "miss"), unsafe_allow_html=True)

    if res["miss"]:
        st.markdown("**어떻게 보완할까요**")
        for tg in res["miss"]:
            st.markdown("<div class='advice'>%s</div>" % reco.gap_advice(d, tg, res["jd_tags"]),
                        unsafe_allow_html=True)

    if res["missing_keywords"]:
        with st.expander("공고에는 있는데 내 포트폴리오에는 없는 단어 %d개"
                         % len(res["missing_keywords"])):
            st.caption("사전에 없는 업계 용어까지 잡아내기 위한 보조 목록입니다. "
                       "억지로 끼워 넣지 말고, 실제로 해본 일을 그 회사가 쓰는 단어로 바꿔 쓰는 데 참고하세요.")
            st.markdown("".join(
                "<span class='pill'>%s <b>%d</b></span>" % (w, n)
                for w, n in res["missing_keywords"]), unsafe_allow_html=True)

    with st.expander("내 이력에서 인식된 역량 %d개" % len(res["my_tags"])):
        by_cat = {}
        for tg in res["my_tags"]:
            by_cat.setdefault(tag_category(tg), []).append(tg)
        for cat, tags in by_cat.items():
            st.markdown("**%s** " % cat + "".join(
                "<span class='pill %s'>%s</span>" % ("hit" if x in res["jd_tags"] else "", tag_label(x))
                for x in tags), unsafe_allow_html=True)
