# -*- coding: utf-8 -*-
"""브라우저 저장소 · 접속한 사람마다 자기 것만 남는다.

배포된 주소에서도 작업 내용이 남게 하려면 어딘가에 저장해야 하는데,
서버에 파일로 두면 다음 접속자에게 남의 이력이 보입니다.
그래서 **각자 브라우저의 localStorage** 에 넣습니다.

  - 데이터는 그 사람 브라우저 안에만 남고 서버에는 저장되지 않습니다.
  - 브라우저가 다르면(다른 PC · 시크릿창) 서로 아무것도 보이지 않습니다.
  - 용량 한도가 있어(보통 5MB) 사진을 많이 넣으면 넘칠 수 있습니다.
    그때는 저장을 건너뛰고 작업 내용 백업(.json 파일)을 안내합니다.
"""

from __future__ import annotations

import json

import streamlit as st

from . import schema

KEY = "portfolio_builder_doc_v1"
SOFT_LIMIT = 3_500_000      # 이보다 크면 저장을 시도하지 않는다 (localStorage 한도 여유분)

_UNAVAILABLE = "browser_store_unavailable"


def _client():
    """LocalStorage 컴포넌트. 설치가 안 됐거나 막혀 있으면 None."""
    if st.session_state.get(_UNAVAILABLE):
        return None
    try:
        from streamlit_local_storage import LocalStorage
        return LocalStorage()
    except Exception:
        st.session_state[_UNAVAILABLE] = True
        return None


def available():
    return _client() is not None


def payload_size(doc):
    return len(json.dumps(doc, ensure_ascii=False).encode("utf-8"))


def too_big(doc):
    return payload_size(doc) > SOFT_LIMIT


# ---------------------------------------------------------------- 읽기
def read_raw():
    """저장된 문자열. 컴포넌트가 아직 값을 못 주면 None."""
    ls = _client()
    if ls is None:
        return None
    try:
        return ls.getItem(KEY)
    except Exception:
        return None


def restore():
    """저장돼 있으면 문서로 되돌린다. -> (doc, 오류메시지)"""
    raw = read_raw()
    if not raw:
        return None, None
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        return schema.normalize(data), None
    except Exception as exc:
        return None, "브라우저에 저장된 내용을 읽지 못했습니다: %s" % exc


# ---------------------------------------------------------------- 쓰기
def save(doc, widget_key="bstore_save"):
    """브라우저에 저장. -> (성공여부, 안내메시지)"""
    ls = _client()
    if ls is None:
        return False, "이 브라우저에서는 자동 저장을 쓸 수 없습니다. 작업 내용을 백업해 두세요."

    size = payload_size(doc)
    if size > SOFT_LIMIT:
        return False, ("내용이 너무 커서(%.1fMB) 브라우저에 담을 수 없습니다. "
                       "사진을 줄이거나 작업 내용을 백업해 두세요." % (size / 1_000_000))
    try:
        ls.setItem(KEY, json.dumps(doc, ensure_ascii=False), key=widget_key)
    except Exception as exc:
        return False, "저장하지 못했습니다: %s" % exc
    st.session_state.bstore_hash = _hash(doc)
    return True, None


def clear(widget_key="bstore_clear"):
    ls = _client()
    if ls is None:
        return False
    try:
        ls.deleteItem(KEY, key=widget_key)
    except Exception:
        return False
    st.session_state.pop("bstore_hash", None)
    return True


# ---------------------------------------------------------------- 자동 저장
def _hash(doc):
    return hash(json.dumps(doc, ensure_ascii=False, sort_keys=True))


def changed_since_save(doc):
    return st.session_state.get("bstore_hash") != _hash(doc)


def autosave(doc, widget_key="bstore_auto"):
    """내용이 실제로 바뀌었을 때만 저장한다. -> 저장했으면 True"""
    if not st.session_state.get("autosave", True):
        return False
    if not changed_since_save(doc):
        return False
    if too_big(doc):
        return False
    ok, _msg = save(doc, widget_key=widget_key)
    return ok
