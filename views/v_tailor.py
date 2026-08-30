# -*- coding: utf-8 -*-
"""추천 수정안 · 구성 조정.

추천 문장은 전부 **사용자가 입력한 데이터 + 공고문**으로 만들어집니다.
없는 경력이 지어내지지 않도록, 원본에 없는 사실은 절대 넣지 않습니다.
"""

from __future__ import annotations

import streamlit as st

from core import schema, reco
from views import common as C


def _snapshot(t):
    st.session_state.undo = schema.clone(t)


def _card(idx, label, text, why, on_apply, applied=False):
    st.markdown(
        "<div class='reco'><div class='lb'>%s</div><div class='tx'>%s</div>"
        "<div class='wy'>%s</div></div>" % (label, (text or "").replace("<", "&lt;"), why),
        unsafe_allow_html=True)
    if st.button("이 안으로 적용" if not applied else "✓ 적용됨",
                 key=C.k("reco", idx), disabled=applied):
        on_apply()
        C.dirty()
        C.bump()
        st.rerun()


def render():
    if C.locked():
        return
    d = C.doc()
    t = C.target()
    C.page_head("추천 수정안",
                "공고와 내 이력을 대조해 만든 초안입니다. 마음에 드는 것만 골라 적용하세요.",
                eyebrow="Suggestions")

    has_jd = bool((t.get("jd_text") or "").strip())
    if not has_jd:
        C.empty_hint("**공고 분석** 탭에서 공고문을 먼저 붙여넣으면 맞춤 추천이 생성됩니다. "
                     "아래에서 문구를 직접 쓸 수도 있습니다.")

    s = reco.suggest(d, t) if has_jd else None

    tab1, tab2, tab3 = st.tabs(["추천 문장", "첫인상 문구 직접 편집", "구성 · 순서"])

    # ================================================ 추천 문장
    with tab1:
        if not s:
            st.caption("공고문을 넣으면 이 자리에 추천이 나타납니다.")
        else:
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("추천안 전체 적용", type="primary", use_container_width=True):
                    _snapshot(t)
                    if s["headlines"]:
                        t["hero_title"] = s["headlines"][0]["text"]
                    if s["taglines"]:
                        t["hero_tagline"] = s["taglines"][0]["text"]
                    t["intro"] = s["intro"]["text"]
                    t["hero_eyebrow"] = s["eyebrow"]
                    if s["metrics"]:
                        t["metrics"] = s["metrics"]
                    t["project_order"] = s["project_order"]
                    t["experience_order"] = s["experience_order"]
                    t["project_emphasis"] = s["emphasis"]
                    C.dirty()
                    C.bump()
                    st.rerun()
            with c2:
                if st.session_state.get("undo"):
                    if st.button("되돌리기 (적용 전으로)"):
                        d["targets"][d["active"]] = st.session_state.pop("undo")
                        C.bump()
                        st.rerun()

            st.divider()
            st.markdown("#### 헤드라인")
            st.caption("첫 화면 가장 큰 문장입니다. 줄바꿈은 그대로 반영됩니다.")
            for i, h in enumerate(s["headlines"]):
                _card("h%d" % i, h["label"], h["text"], h["why"],
                      lambda h=h: (_snapshot(t), t.update({"hero_title": h["text"],
                                                           "hero_eyebrow": s["eyebrow"]})),
                      applied=t.get("hero_title") == h["text"])

            if s["taglines"]:
                st.markdown("#### 한 줄 소개")
                for i, g in enumerate(s["taglines"]):
                    _card("g%d" % i, g["label"], g["text"], g["why"],
                          lambda g=g: (_snapshot(t), t.update({"hero_tagline": g["text"]})),
                          applied=t.get("hero_tagline") == g["text"])

            st.markdown("#### 자기소개 본문")
            _card("intro", "공고 기준으로 재구성한 초안", s["intro"]["text"], s["intro"]["why"],
                  lambda: (_snapshot(t), t.update({"intro": s["intro"]["text"]})),
                  applied=t.get("intro") == s["intro"]["text"])

            if s["metrics"]:
                st.markdown("#### 핵심 지표 4개")
                preview = "   ".join("%s %s" % (m["value"], m["label"]) for m in s["metrics"])
                _card("metrics", "공고 적합도 순으로 뽑은 지표", preview,
                      "첫 화면 하단에 크게 노출됩니다. 공고가 중시하는 항목이 앞에 오도록 정렬했습니다.",
                      lambda: (_snapshot(t), t.update({"metrics": s["metrics"]})),
                      applied=t.get("metrics") == s["metrics"])

            if s["checklist"]:
                st.divider()
                st.markdown("#### 제출 전 체크리스트")
                for line in s["checklist"]:
                    st.markdown("<div class='advice'>%s</div>" % line, unsafe_allow_html=True)

    # ================================================ 직접 편집
    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            C.text_field("상단 라벨", t, "hero_eyebrow",
                         placeholder="for ○○회사 · 마케팅PM")
            C.area_field("헤드라인", t, "hero_title", height=100,
                         help="줄바꿈이 그대로 반영됩니다.")
            C.area_field("한 줄 소개", t, "hero_tagline", height=110)
        with c2:
            C.area_field("자기소개 본문", t, "intro", height=300,
                         help="빈 줄로 문단을 나눕니다.")

        st.markdown("**핵심 지표 4개**")
        metrics = t.setdefault("metrics", [])
        while len(metrics) < 4:
            metrics.append({"value": "", "label": ""})
        cols = st.columns(4)
        for i in range(4):
            with cols[i]:
                C.text_field("숫자 %d" % (i + 1), metrics[i], "value", wid=C.k("mv", i))
                C.text_field("라벨 %d" % (i + 1), metrics[i], "label", wid=C.k("ml", i))

    # ================================================ 구성
    with tab3:
        st.markdown("#### 표기 설정")
        c1, c2 = st.columns(2)
        with c1:
            hide = st.checkbox("구체적인 수치 숨기기", value=bool(t.get("hide_numbers", True)),
                               key=C.k("hidenum"),
                               help="켜면 프로젝트마다 적어 둔 '숫자 없는 문장'으로 바뀝니다. "
                                    "대행사에서 다룬 광고주 성과처럼 대외비일 수 있는 숫자에 쓰세요.")
            if hide != t.get("hide_numbers"):
                t["hide_numbers"] = hide
                C.dirty()
                st.rerun()

            cu = d["base"]["custom"]
            has_answer = any((x.get("a") or "").strip() for x in cu.get("items") or [])
            on = st.checkbox("자유 섹션 노출 (%s)" % (cu.get("title") or "제목 없음"),
                             value=bool(t.get("custom_enabled")), key=C.k("cuon"),
                             disabled=not has_answer,
                             help="답변을 하나라도 적어야 켤 수 있습니다.")
            if on != t.get("custom_enabled"):
                t["custom_enabled"] = on
                C.dirty()
            if not has_answer:
                st.caption("→ **내 정보 · 자유 섹션** 에서 답변을 적으면 켤 수 있습니다.")
        with c2:
            accent = st.color_picker("강조 색", t.get("accent") or "#2C5F8A", key=C.k("accent"),
                                     help="웹페이지와 PPT 의 포인트 색이 함께 바뀝니다.")
            if accent != t.get("accent"):
                t["accent"] = accent
                C.dirty()

        st.divider()
        st.markdown("#### 프로젝트 순서 · 노출")
        if s and st.button("공고 적합도 순으로 정렬"):
            _snapshot(t)
            t["project_order"] = s["project_order"]
            t["experience_order"] = s["experience_order"]
            C.dirty()
            C.bump()
            st.rerun()

        projects = schema.ordered_projects(d, t)
        all_ids = [p["id"] for p in d["base"]["projects"]]
        order = t.setdefault("project_order", [])
        if sorted(order) != sorted(all_ids):
            order[:] = [p["id"] for p in projects] + [i for i in all_ids
                                                      if i not in [p["id"] for p in projects]]

        visible = t.setdefault("project_visible", {})
        emphasis = t.setdefault("project_emphasis", {})
        jd_tags = s["analysis"]["jd_tags"] if s else []

        for i, pid in enumerate(list(order)):
            pr = schema.project_by_id(d, pid)
            if not pr:
                continue
            hits = [x for x in (pr.get("tags") or []) if x in jd_tags]
            badge = " · 공고 일치 %d개" % len(hits) if jd_tags else ""
            with st.expander("%02d. %s%s" % (i + 1, pr.get("title") or "(제목 없음)", badge)):
                c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
                with c1:
                    if st.button("▲ 위로", key=C.k("po", "up", i), disabled=i == 0,
                                 use_container_width=True):
                        order[i - 1], order[i] = order[i], order[i - 1]
                        C.dirty()
                        C.bump()
                        st.rerun()
                with c2:
                    if st.button("▼ 아래로", key=C.k("po", "dn", i), disabled=i >= len(order) - 1,
                                 use_container_width=True):
                        order[i + 1], order[i] = order[i], order[i + 1]
                        C.dirty()
                        C.bump()
                        st.rerun()
                with c3:
                    show = st.checkbox("노출", value=visible.get(pid, True), key=C.k("pv", i))
                    if show != visible.get(pid, True):
                        visible[pid] = show
                        C.dirty()
                with c4:
                    if s and pid in s["emphasis"]:
                        if st.button("추천 강조 문구 적용", key=C.k("pe", i), use_container_width=True):
                            emphasis[pid] = s["emphasis"][pid]
                            C.dirty()
                            C.bump()
                            st.rerun()
                val = st.text_area("강조 문구 (이 프로젝트를 왜 앞에 뒀는지)",
                                   emphasis.get(pid, ""), height=90, key=C.k("pet", i),
                                   placeholder="비워 두면 표시되지 않습니다.")
                if val != emphasis.get(pid, ""):
                    emphasis[pid] = val
                    C.dirty()

        st.divider()
        st.markdown("#### 경력 순서")
        exps = schema.ordered_experience(d, t)
        eorder = t.setdefault("experience_order", [])
        eorder[:] = [e["id"] for e in exps]
        for i, ex in enumerate(exps):
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.write("**%d.** %s · %s" % (i + 1, ex.get("org", ""), ex.get("role", "")))
            with c2:
                if st.button("▲", key=C.k("eo", "up", i), disabled=i == 0, use_container_width=True):
                    eorder[i - 1], eorder[i] = eorder[i], eorder[i - 1]
                    C.dirty()
                    C.bump()
                    st.rerun()
            with c3:
                if st.button("▼", key=C.k("eo", "dn", i), disabled=i >= len(eorder) - 1,
                             use_container_width=True):
                    eorder[i + 1], eorder[i] = eorder[i], eorder[i + 1]
                    C.dirty()
                    C.bump()
                    st.rerun()
