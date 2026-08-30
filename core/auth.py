# -*- coding: utf-8 -*-
"""비밀번호 잠금.

링크를 아는 사람 누구나 들어올 수 있는 걸 막습니다.

원칙
  - 비밀번호는 **코드나 저장소에 절대 넣지 않습니다.**
    Streamlit Cloud 의 Secrets 나 환경변수로만 넣습니다.
  - 비밀번호가 설정돼 있지 않으면 **열어 두지 않고 막습니다.**
    설정을 깜빡했을 때 앱이 공개돼 버리는 쪽이 훨씬 위험하기 때문입니다.
  - 내 PC(로컬 모드)에서는 묻지 않습니다.
"""

from __future__ import annotations

import hashlib
import hmac
import os

import streamlit as st

from . import io_utils

SESSION_KEY = "auth_ok"
MAX_TRIES = 6


def _secret(*names):
    """secrets.toml 과 환경변수에서 값을 찾는다."""
    for name in names:
        try:
            if name in st.secrets:
                return str(st.secrets[name])
        except Exception:
            pass
        try:
            block = st.secrets.get("auth", None)
            if block and name in block:
                return str(block[name])
        except Exception:
            pass
        val = os.environ.get(name.upper()) or os.environ.get(name)
        if val:
            return str(val)
    return None


def configured():
    """설정된 비밀번호 (평문 또는 sha256). -> (값, 해시여부)"""
    digest = _secret("app_password_sha256", "password_sha256")
    if digest:
        return digest.strip().lower(), True
    plain = _secret("app_password", "password", "portfolio_password")
    if plain:
        return plain, False
    return None, False


def needed():
    """이 환경에서 비밀번호를 물어야 하는가."""
    if io_utils.is_local_mode():
        return False                     # 내 PC 에서 혼자 쓸 때는 안 묻는다
    return True


def verify(entered):
    value, hashed = configured()
    if not value or not entered:
        return False
    if hashed:
        got = hashlib.sha256(entered.encode("utf-8")).hexdigest()
        return hmac.compare_digest(got, value)
    return hmac.compare_digest(entered, value)


def gate():
    """통과했으면 True. 아니면 잠금 화면을 그리고 False."""
    if not needed() or st.session_state.get(SESSION_KEY):
        return True

    value, _hashed = configured()

    st.markdown("### 🔒 포트폴리오 빌더")
    if not value:
        # 설정이 안 된 채 배포된 상태 — 열어 주지 않는다
        st.error("비밀번호가 설정되지 않아 접속할 수 없습니다. "
                 "앱 관리자에게 문의해 주세요.", icon=":material/lock:")
        with st.expander("관리자라면 — 설정 방법"):
            st.markdown("""
Streamlit Cloud 앱 화면에서 **Manage app → Settings → Secrets** 에 아래를 넣고 저장하세요.

```toml
app_password = "정한_비밀번호"
```

비밀번호를 그대로 두기 싫으면 SHA-256 해시를 대신 넣어도 됩니다.

```toml
app_password_sha256 = "해시값"
```

로컬에서는 `app/data/.local` 파일이 있으면 비밀번호를 묻지 않습니다.
""")
        return False

    tries = st.session_state.get("auth_tries", 0)
    if tries >= MAX_TRIES:
        st.error("비밀번호를 여러 번 틀렸습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.")
        return False

    st.caption("초대받은 분만 사용할 수 있습니다. 비밀번호를 입력해 주세요.")
    with st.form("auth_form"):
        entered = st.text_input("비밀번호", type="password",
                                label_visibility="collapsed",
                                placeholder="비밀번호")
        sent = st.form_submit_button("들어가기", type="primary")

    if sent:
        if verify(entered):
            st.session_state[SESSION_KEY] = True
            st.session_state.pop("auth_tries", None)
            st.rerun()
        else:
            st.session_state.auth_tries = tries + 1
            st.error("비밀번호가 맞지 않습니다. (%d/%d)"
                     % (st.session_state.auth_tries, MAX_TRIES))

    st.caption("입력한 비밀번호는 어디에도 저장되거나 기록되지 않습니다.")
    return False


def logout_button():
    """사이드바에 두는 잠금 버튼."""
    if not needed() or not st.session_state.get(SESSION_KEY):
        return
    if st.button("🔒 잠그기", use_container_width=True,
                 help="이 브라우저에서 로그아웃합니다. 저장해 둔 내용은 그대로 남습니다."):
        st.session_state.pop(SESSION_KEY, None)
        st.rerun()


def passed():
    """통과한 상태인가 (비밀번호가 필요 없는 환경 포함)."""
    return (not needed()) or bool(st.session_state.get(SESSION_KEY))
