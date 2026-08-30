# -*- coding: utf-8 -*-
"""공고 분석 · 필수/우대 요구사항, 넣어야 할 키워드, 보완 방법."""

from __future__ import annotations

import streamlit as st

from core import reco, jd, extract
from core import schema
from core.tags import tag_label, tag_category
from views import common as C

GROUP_ICON = {"필수": "🔴", "담당업무": "🔵", "우대": "⚪", "기타": "⚪"}


def _target_form(t):
    c1, c2 = st.columns(2)
    with c1:
        C.text_field("프로필 이름", t, "label", placeholder="○○회사 · 마케팅PM",
                     help="사이드바 목록에 표시되는 이름입니다.")
        C.text_field("지원 회사", t, "company", placeholder="지원하는 회사 이름")
    with c2:
        C.text_field("공고명 · 포지션", t, "position", placeholder="공고에 적힌 포지션명 그대로")
        C.text_field("마감일", t, "deadline", placeholder="2026-08-16")

    c1, c2 = st.columns([4, 1])
    with c1:
        C.text_field("공고 URL", t, "jd_url", placeholder="https://...")
    with c2:
        st.write("")
        st.write("")
        if st.button("링크에서 가져오기", use_container_width=True,
                     disabled=not (t.get("jd_url") or "").strip()):
            _fetch_url(t)

    _fetch_message()

    C.area_field("공고문 전문", t, "jd_text", height=240,
                 placeholder="담당업무 · 자격요건 · 우대사항을 그대로 붙여넣으세요. "
                             "제목까지 같이 넣으면 필수와 우대를 구분해 분석합니다.")


def _fetch_url(t):
    with st.spinner("공고를 읽는 중..."):
        text, err, info = extract.jd_from_url(t.get("jd_url"))
    if err:
        st.session_state.jd_fetch_msg = ("warn", err)
    elif text:
        t["jd_text"] = text
        C.dirty()
        note = "공고를 가져왔습니다 (%s · %d자)." % (info.get("how", ""), info.get("chars", 0))
        if info.get("thin"):
            st.session_state.jd_fetch_msg = (
                "warn", note + " 다만 **본문이 짧아 메뉴만 긁어왔을 수 있습니다.** "
                               "아래 내용을 확인하고, 이상하면 직접 붙여넣어 주세요.")
        else:
            st.session_state.jd_fetch_msg = ("ok", note + " 필요 없는 부분은 지워 주세요.")
        C.bump()
    st.rerun()


def _fetch_message():
    msg = st.session_state.get("jd_fetch_msg")
    if msg:
        (st.success if msg[0] == "ok" else st.warning)(msg[1])


def _score_row(req, res):
    left, right = st.columns([1, 2])
    with left:
        st.metric("공고 충족률", "%d%%" % req["score"],
                  help="필수 요구사항에 더 큰 가중치를 둔 값입니다.")
        st.progress(req["score"] / 100.0)
    with right:
        cols = st.columns(len(req["groups"]) or 1)
        for col, g in zip(cols, req["groups"]):
            col.metric("%s %s" % (GROUP_ICON.get(g["label"], ""), g["label"]),
                       "%d / %d" % (len(g["hit"]), len(g["tags"])))
        if not req["has_structure"]:
            st.caption("공고에서 '자격요건 · 우대사항' 같은 제목을 찾지 못해 전체를 필수로 봤습니다. "
                       "제목까지 붙여넣으면 더 정확해집니다.")


def _requirement_cards(doc, req):
    for g in req["groups"]:
        if not g["tags"]:
            continue
        st.markdown("##### %s %s 요구사항 · %d개 중 %d개 충족"
                    % (GROUP_ICON.get(g["label"], ""), g["label"],
                       len(g["tags"]), len(g["hit"])))

        for t in g["tags"]:
            ok = t in g["hit"]
            ev = g["evidence"].get(t) or []
            if ok:
                proof = " · ".join("%s 「%s」" % (kind, name.strip()) for kind, name in ev[:2])
                st.markdown(
                    "<div class='req ok'><b>✅ %s</b>"
                    "<span class='req-why'>%s</span></div>"
                    % (tag_label(t), proof or "이력에 태그가 붙어 있습니다."),
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    "<div class='req no'><b>❌ %s</b>"
                    "<span class='req-why'>%s</span></div>"
                    % (tag_label(t), reco.gap_advice(doc, t, [])),
                    unsafe_allow_html=True)
        st.write("")


def _keyword_table(plan):
    if not plan:
        return
    st.caption("공고가 쓰는 표현입니다. **없는 경험을 지어내라는 뜻이 아니라**, "
               "실제로 해본 일을 그 회사가 쓰는 단어로 바꿔 쓰라는 목록입니다.")

    missing = [k for k in plan if not k["used"]]
    using = [k for k in plan if k["used"]]

    if missing:
        st.markdown("**아직 안 쓰고 있는 표현 %d개**" % len(missing))
        rows = "".join(
            "<tr><td>%s %s</td><td class='k-w'>%s</td><td class='k-kind'>%s</td></tr>"
            % (GROUP_ICON.get(k["group"], ""), k["group"], k["label"], k["kind"])
            for k in missing)
        st.markdown("<table class='kw-table'><thead><tr><th>구분</th><th>키워드</th>"
                    "<th>종류</th></tr></thead><tbody>%s</tbody></table>" % rows,
                    unsafe_allow_html=True)
    if using:
        st.markdown("**이미 쓰고 있는 표현 %d개**" % len(using))
        st.markdown("".join("<span class='pill hit'>%s</span>" % k["label"] for k in using),
                    unsafe_allow_html=True)


def render():
    if C.locked():
        return
    d = C.doc()
    t = C.target()
    C.page_head("공고 분석", "공고를 필수 · 담당업무 · 우대로 나눠 읽고, "
                            "내 이력으로 무엇이 증명되는지 대조합니다.")
    _target_form(t)

    if not (t.get("jd_text") or "").strip():
        C.empty_hint("공고문을 붙여넣으면 필수 능력과 넣어야 할 키워드가 여기에 나타납니다.")
        return

    st.divider()
    res = reco.analyze(d, t)
    req = jd.requirements(d, t["jd_text"], res["my_tags"])
    _score_row(req, res)

    st.divider()
    tab1, tab2, tab0, tab3 = st.tabs(
        ["필수 능력 점검", "들어가야 할 키워드", "수정 포인트", "내 역량 목록"])

    with tab1:
        if not req["groups"]:
            st.warning("공고문에서 아는 역량 표현을 찾지 못했습니다. "
                       "담당업무·자격요건 문단을 더 붙여넣어 보세요.")
        else:
            _requirement_cards(d, req)

    with tab2:
        plan = jd.keyword_plan(d, t["jd_text"], schema.my_text(d, t),
                               my_tags=res["my_tags"])
        _keyword_table(plan)

    with tab0:
        points = jd.fix_points(d, t, res["my_tags"])
        if not points:
            st.success("지금 구성으로 크게 고칠 곳이 없습니다.")
        else:
            st.caption("위에서부터 손대면 됩니다. 순서 → 문장 → 키워드 → 구성 순으로 정렬했습니다.")
            for i, p in enumerate(points, 1):
                st.markdown("<div class='fix'><span class='fix-k'>%s</span>"
                            "<b>%d.</b> %s</div>" % (p["kind"], i, p["text"]),
                            unsafe_allow_html=True)

    with tab3:
        by_cat = {}
        for tg in res["my_tags"]:
            by_cat.setdefault(tag_category(tg), []).append(tg)
        if not by_cat:
            st.caption("아직 이력에 태그가 없습니다. 경력·프로젝트를 입력하면 자동으로 붙습니다.")
        for cat, tags in by_cat.items():
            st.markdown("**%s** " % cat + "".join(
                "<span class='pill %s'>%s</span>"
                % ("hit" if x in res["jd_tags"] else "", tag_label(x)) for x in tags),
                unsafe_allow_html=True)
