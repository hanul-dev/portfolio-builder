# -*- coding: utf-8 -*-
"""자동 만들기 · 공고 + 이력서 파일 -> 포트폴리오 한 번에.

이 앱의 첫 화면입니다. 여기서 끝나도 결과물이 나오고,
더 다듬고 싶으면 나머지 탭으로 넘어가면 됩니다.
"""

from __future__ import annotations

import streamlit as st

from core import schema, extract, parse_resume, reco
from core.tags import tag_label
from views import common as C

MAX_MB = 15


def _step(n, title, done=False):
    st.markdown("#### %s %d단계 · %s" % ("✅" if done else "▸", n, title))


# ---------------------------------------------------------------- 1단계
def _jd_step():
    t = C.target()
    _step(1, "지원할 공고", done=bool((t.get("jd_text") or "").strip()))
    st.caption("공고명과 링크를 넣으면 요구 역량을 뽑아냅니다. "
               "링크를 못 읽는 사이트가 많으니, 안 되면 내용을 붙여넣어 주세요.")

    c1, c2 = st.columns(2)
    with c1:
        C.text_field("지원 회사", t, "company", placeholder="지원하는 회사 이름")
    with c2:
        C.text_field("공고명 · 포지션", t, "position", placeholder="공고에 적힌 포지션명 그대로")

    c1, c2 = st.columns([4, 1])
    with c1:
        C.text_field("공고 링크", t, "jd_url", placeholder="https://...")
    with c2:
        st.write("")
        st.write("")
        if st.button("링크에서 가져오기", use_container_width=True,
                     disabled=not (t.get("jd_url") or "").strip()):
            with st.spinner("공고를 읽는 중..."):
                text, err = extract.jd_from_url(t.get("jd_url"))
            if err:
                st.session_state.jd_fetch_msg = ("warn", err)
            elif text:
                t["jd_text"] = text
                C.dirty()
                st.session_state.jd_fetch_msg = ("ok", "공고를 가져왔습니다. 아래에서 확인하고, "
                                                       "필요 없는 부분은 지워 주세요.")
                C.bump()
            st.rerun()

    msg = st.session_state.get("jd_fetch_msg")
    if msg:
        (st.success if msg[0] == "ok" else st.warning)(msg[1])

    C.area_field("공고문", t, "jd_text", height=200,
                 placeholder="담당업무 · 자격요건 · 우대사항을 붙여넣으세요. 많을수록 정확합니다.")

    extra = st.text_input("직무 키워드 (선택)", st.session_state.get("auto_keywords", ""),
                          key=C.k("autokw"),
                          placeholder="공고에 없지만 이 직무에서 중요한 말들. 예: 그로스, CRM, 리텐션",
                          help="쉼표로 구분해 적으면 공고문과 함께 분석합니다.")
    st.session_state.auto_keywords = extra


# ---------------------------------------------------------------- 2단계
def _resume_step():
    parsed = st.session_state.get("auto_report")
    _step(2, "이력서 파일", done=bool(parsed))
    st.caption("PDF 또는 Word(.docx) 파일을 올리면 경력·프로젝트·학력을 자동으로 나눠 읽습니다. "
               "파일은 서버에 저장되지 않습니다.")

    up = st.file_uploader("이력서 파일", type=["pdf", "docx", "txt"], key=C.k("resume"),
                          label_visibility="collapsed")

    if up is not None:
        if up.size > MAX_MB * 1024 * 1024:
            st.error("파일이 너무 큽니다 (%d MB 까지)." % MAX_MB)
        else:
            text, err = extract.file_text(up.read(), up.name)
            if err:
                st.error(err)
            elif st.button("이력서 읽기", type="primary", key=C.k("doparse")):
                _do_parse(text, up.name)

    # 붙여넣기는 폼으로 감싼다. 그래야 Ctrl+Enter 를 몰라도
    # 버튼 한 번으로 내용이 전달된다.
    with st.expander("파일 대신 내용을 붙여넣기"):
        with st.form(key=C.k("pasteform")):
            pasted = st.text_area(
                "이력서 내용", height=200,
                placeholder="한글(.hwp)을 쓰거나 파일 변환이 번거로우면 "
                            "이력서 내용을 그대로 복사해 붙여넣으세요.")
            sent = st.form_submit_button("붙여넣은 내용 읽기", type="primary")
        if sent:
            if pasted.strip():
                _do_parse(pasted, "붙여넣은 내용")
            else:
                st.warning("내용이 비어 있습니다.")


def _do_parse(text, source):
    with st.spinner("이력서를 나눠 읽는 중..."):
        doc, report = parse_resume.parse(text)
    st.session_state.auto_doc = doc
    st.session_state.auto_report = report
    st.session_state.auto_source = source
    C.bump()
    st.rerun()


# ---------------------------------------------------------------- 3단계
def _review_step():
    report = st.session_state.get("auto_report")
    if not report:
        return False

    _step(3, "이렇게 읽었습니다", done=True)
    st.caption("규칙으로 나눠 읽은 결과라 틀릴 수 있습니다. "
               "여기서 대충 맞으면 만들고, 세부 수정은 그다음에 하세요.")

    conf = report.get("confidence")
    if conf == "low":
        st.error("이력서 형식을 거의 알아보지 못했습니다. 표나 이미지가 많은 파일일 수 있습니다. "
                 "위의 **붙여넣기**로 다시 시도하거나, 비워둔 채로 진행하고 직접 입력하셔도 됩니다.",
                 icon=":material/error:")
    elif conf == "medium":
        st.warning("일부만 읽었습니다. 아래 숫자를 보고 빠진 항목이 많으면 붙여넣기로 다시 해보세요.",
                   icon=":material/warning:")

    found = report["found"]
    cols = st.columns(len(found))
    for col, (label, n) in zip(cols, found.items()):
        col.metric(label, n)

    p = report["person"]
    bits = [x for x in [p.get("name"), p.get("birth"), p.get("phone"), p.get("email"),
                        p.get("location")] if x]
    st.write("**인적사항** · " + (" · ".join(bits) if bits else "찾지 못했습니다"))

    doc = st.session_state.get("auto_doc")
    if doc:
        b = doc["base"]
        if b["experience"]:
            with st.expander("경력 %d건 미리보기" % len(b["experience"]), expanded=True):
                for ex in b["experience"]:
                    line = " · ".join(x for x in [ex["org"], ex["role"], ex["period"]] if x)
                    st.markdown("- **%s**" % line)
                    if ex["summary"]:
                        st.caption("  " + ex["summary"][:120])
        if b["projects"]:
            with st.expander("프로젝트 %d건 미리보기" % len(b["projects"]), expanded=True):
                for pr in b["projects"]:
                    st.markdown("- **%s** %s · 실행 %d개" % (
                        pr["title"], pr["period"], len(pr["actions"])))
        if report.get("leftover"):
            with st.expander("섹션으로 나누지 못한 글"):
                st.caption("버리지 않고 남겨 뒀습니다. 필요한 문장은 복사해서 쓰세요.")
                st.text(report["leftover"][:2000])
    return True


# ---------------------------------------------------------------- 4단계
def _build_step():
    _step(4, "포트폴리오 만들기")

    auto_doc = st.session_state.get("auto_doc")
    t = C.target()
    has_jd = bool((t.get("jd_text") or "").strip())
    has_resume = bool(auto_doc)

    if not has_resume:
        C.empty_hint("이력서를 먼저 읽어 주세요. 공고만으로는 포트폴리오를 만들 수 없습니다.")
        return
    if not has_jd:
        st.warning("공고문이 비어 있습니다. 이대로 만들면 순서·강조 문구 추천 없이 "
                   "이력만 정리됩니다.", icon=":material/info:")

    cur = C.doc()
    filled = bool(cur["base"]["projects"] or cur["base"]["experience"]
                  or cur["base"]["person"].get("name"))
    if filled:
        st.warning("지금 입력돼 있는 내용이 **모두 지워지고** 이력서에서 읽은 내용으로 바뀝니다. "
                   "필요하면 먼저 사이드바에서 JSON 을 내려받아 두세요.", icon=":material/warning:")

    if not st.button("이 내용으로 포트폴리오 만들기", type="primary", use_container_width=True):
        return

    # ---- 새 문서 조립
    new = schema.clone(auto_doc)
    target = schema.active_target(new)
    for key in ("company", "position", "jd_url", "jd_text", "deadline"):
        target[key] = t.get(key, "")
    label = " · ".join(x for x in [t.get("company"), t.get("position")] if x)
    target["label"] = label or "새 지원처"

    extra = (st.session_state.get("auto_keywords") or "").strip()
    if extra:                       # 직접 적은 키워드도 분석에 포함
        target["jd_text"] = (target["jd_text"] + "\n" + extra).strip()

    resume_intro = target.get("intro", "")

    if (target.get("jd_text") or "").strip():
        s = reco.suggest(new, target)
        if s["headlines"]:
            target["hero_title"] = s["headlines"][0]["text"]
        if s["taglines"]:
            target["hero_tagline"] = s["taglines"][0]["text"]
        target["hero_eyebrow"] = s["eyebrow"]
        target["intro"] = s["intro"]["text"]
        if s["metrics"]:
            target["metrics"] = s["metrics"]
        target["project_order"] = s["project_order"]
        target["experience_order"] = s["experience_order"]
        target["project_emphasis"] = s["emphasis"]

    st.session_state.doc = new
    st.session_state.resume_intro = resume_intro
    st.session_state.built = True
    C.dirty()
    C.bump()
    st.rerun()


def _after_build():
    if not st.session_state.get("built"):
        return
    d = C.doc()
    t = C.target()
    st.success("포트폴리오를 만들었습니다.", icon=":material/check_circle:")

    res = reco.analyze(d, t)
    c1, c2, c3 = st.columns(3)
    c1.metric("공고 충족률", "%d%%" % res["score"])
    c2.metric("프로젝트", "%d건" % len(d["base"]["projects"]))
    c3.metric("경력", "%d건" % len(d["base"]["experience"]))

    if res["miss"]:
        st.caption("보완이 필요한 요구사항: " + ", ".join(tag_label(x) for x in res["miss"][:6]))

    st.markdown("**다음으로 할 일**")
    st.markdown("""
1. **미리보기 · 다운로드** 에서 결과를 보고 HTML · PPT 를 받으세요.
2. 문장이 어색하면 **내 정보** · **경력 · 프로젝트** 에서 고치세요. 자동으로 읽은 결과라 다듬을 곳이 있습니다.
3. **추천 수정안** 에서 다른 헤드라인·자기소개 후보를 볼 수 있습니다.
""")

    if st.session_state.get("resume_intro"):
        if st.button("자기소개를 이력서 원문 그대로 되돌리기"):
            t["intro"] = st.session_state["resume_intro"]
            C.dirty()
            C.bump()
            st.rerun()


# ---------------------------------------------------------------- 진입점
def render():
    C.page_head("자동 만들기",
                "공고와 이력서 파일만 있으면 됩니다. 나머지는 앱이 맞춰서 정리합니다.")
    _after_build()
    st.divider()
    _jd_step()
    st.divider()
    _resume_step()
    st.divider()
    if _review_step():
        st.divider()
    _build_step()
