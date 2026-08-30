# -*- coding: utf-8 -*-
"""페이지 공용 헬퍼."""

from __future__ import annotations

import streamlit as st

from core import schema, io_utils
from core.tags import all_tags, tag_label


# ---------------------------------------------------------------- 상태
def doc():
    return st.session_state.doc


def target():
    return schema.active_target(st.session_state.doc)


def bump():
    """위젯 키를 갈아끼워, 코드로 바꾼 값이 화면에 즉시 반영되게 한다."""
    st.session_state.nonce = st.session_state.get("nonce", 0) + 1


def k(*parts):
    return "_".join([str(p) for p in parts] + [str(st.session_state.get("nonce", 0))])


def dirty():
    st.session_state.dirty = True


# ---------------------------------------------------------------- 위젯
def text_field(label, obj, key, help=None, placeholder=None, wid=None):
    val = st.text_input(label, obj.get(key, ""), key=wid or k("f", id(obj), key),
                        help=help, placeholder=placeholder)
    if val != obj.get(key, ""):
        obj[key] = val
        dirty()
    return val


def area_field(label, obj, key, height=120, help=None, placeholder=None, wid=None):
    val = st.text_area(label, obj.get(key, ""), height=height, key=wid or k("a", id(obj), key),
                       help=help, placeholder=placeholder)
    if val != obj.get(key, ""):
        obj[key] = val
        dirty()
    return val


def tag_field(obj, key="tags", label="역량 태그", help=None):
    cur = [t for t in (obj.get(key) or []) if t in all_tags()]
    val = st.multiselect(label, all_tags(), default=cur, format_func=tag_label,
                         key=k("t", id(obj), key), help=help)
    if val != obj.get(key):
        obj[key] = val
        dirty()
    return val


def lines_field(label, obj, key, height=120, help=None, placeholder=None):
    """리스트를 한 줄에 하나씩 편집."""
    cur = "\n".join(obj.get(key) or [])
    val = st.text_area(label, cur, height=height, key=k("l", id(obj), key),
                       help=help, placeholder=placeholder)
    if val != cur:
        obj[key] = [x.strip() for x in val.split("\n") if x.strip()]
        dirty()
    return obj[key]


def image_field(label, obj, key="image", help=None):
    col1, col2 = st.columns([1, 2])
    with col1:
        if obj.get(key):
            st.image(obj[key], use_container_width=True)
            if st.button("이미지 삭제", key=k("imgdel", id(obj), key)):
                obj[key] = ""
                dirty()
                st.rerun()
        else:
            st.caption("이미지 없음")
    with col2:
        up = st.file_uploader(label, type=["png", "jpg", "jpeg", "webp"],
                              key=k("img", id(obj), key), help=help)
        if up is not None:
            obj[key] = io_utils.to_data_uri(up.read())
            dirty()
            st.rerun()


def move_buttons(lst, idx, key_prefix):
    """리스트 항목 위/아래 이동 + 삭제. 바뀌면 True."""
    c1, c2, c3 = st.columns(3)
    changed = False
    with c1:
        if st.button("▲ 위로", key=k(key_prefix, "up", idx), disabled=idx == 0,
                     use_container_width=True):
            lst[idx - 1], lst[idx] = lst[idx], lst[idx - 1]
            changed = True
    with c2:
        if st.button("▼ 아래로", key=k(key_prefix, "dn", idx), disabled=idx >= len(lst) - 1,
                     use_container_width=True):
            lst[idx + 1], lst[idx] = lst[idx], lst[idx + 1]
            changed = True
    with c3:
        if st.button("삭제", key=k(key_prefix, "del", idx), use_container_width=True):
            lst.pop(idx)
            changed = True
    if changed:
        dirty()
        bump()
        st.rerun()
    return changed


def _render_field(item, fkey, flabel, key_prefix, i):
    if fkey == "tags":
        tag_field(item)
    elif fkey == "bar":
        val = st.slider(flabel, 0, 100, int(item.get("bar") or 80), 5,
                        key=k(key_prefix, "bar", i))
        if val != item.get("bar"):
            item["bar"] = val
            dirty()
    elif fkey == "desc":
        area_field(flabel, item, fkey, height=100, wid=k(key_prefix, fkey, i))
    else:
        text_field(flabel, item, fkey, wid=k(key_prefix, fkey, i))


def simple_list_editor(items, fields, key_prefix, new_item, label_of, add_label="+ 항목 추가"):
    """{키: 라벨} 정의로 반복 항목을 편집한다. 좁은 칸은 3개씩 나눠 배치."""
    wide = [f for f in fields if f in ("tags", "desc")]
    narrow = [f for f in fields if f not in wide]

    for i, item in enumerate(list(items)):
        with st.expander(label_of(item) or "(제목 없음)", expanded=False):
            for start in range(0, len(narrow), 3):
                chunk = narrow[start:start + 3]
                cols = st.columns(len(chunk))
                for col, fkey in zip(cols, chunk):
                    with col:
                        _render_field(item, fkey, fields[fkey], key_prefix, i)
            for fkey in wide:
                _render_field(item, fkey, fields[fkey], key_prefix, i)
            st.divider()
            move_buttons(items, i, key_prefix)

    if st.button(add_label, key=k(key_prefix, "add")):
        items.append(dict(new_item))
        dirty()
        bump()
        st.rerun()


# ---------------------------------------------------------------- 레이아웃
def page_head(title, desc="", eyebrow=""):
    """페이지 머리. 작은 라벨 + 제목 + 설명."""
    st.markdown(
        "<div class='page-head'>%s<h1 class='page-title'>%s</h1>%s</div>"
        % (("<span class='page-eyebrow'>%s</span>" % _esc(eyebrow)) if eyebrow else "",
           _esc(title),
           ("<p class='page-sub'>%s</p>" % _esc(desc)) if desc else ""),
        unsafe_allow_html=True)


def step(n, title, done=False):
    """1단계 · 2단계 … 표시."""
    st.markdown(
        "<div class='step%s'><span class='step-n'>%s</span>"
        "<span class='step-t'>%s</span></div>"
        % (" done" if done else "", "✓" if done else n, _esc(title)),
        unsafe_allow_html=True)


def stat_cards(items, highlight=0):
    """[(값, 라벨), …] 를 카드 줄로."""
    cells = "".join(
        "<div class='stat%s'><b>%s</b><span>%s</span></div>"
        % (" hi" if i < highlight else "", _esc(v), _esc(l))
        for i, (v, l) in enumerate(items))
    st.markdown("<div class='stat-row'>%s</div>" % cells, unsafe_allow_html=True)


def _esc(text):
    import html as _h
    return _h.escape(str(text or ""))


def empty_hint(msg):
    st.info(msg, icon=":material/lightbulb:")


def locked():
    """비밀번호를 아직 통과하지 못했으면 True (그리고 잠금 화면을 그린다).

    각 화면 맨 앞에서 호출합니다. 페이지 함수를 감싸는 방식은
    st.navigation 이 사이드바를 못 만들게 해서 이렇게 했습니다.
    """
    from core import auth
    return not auth.gate()
