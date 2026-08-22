# -*- coding: utf-8 -*-
"""이미지 · JSON 입출력."""

from __future__ import annotations

import base64
import io
import json
import os

from . import schema

MAX_PX = 1400
JPEG_QUALITY = 82


def to_data_uri(raw, max_px=MAX_PX):
    """업로드한 이미지를 적당히 줄여 data URI 문자열로 만든다.

    포트폴리오 JSON 하나에 이미지까지 전부 들어가야
    다른 기기에서 불러왔을 때 그림이 깨지지 않습니다.
    """
    if not raw:
        return ""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw))
        has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        if max(im.size) > max_px:
            ratio = max_px / float(max(im.size))
            im = im.resize((max(1, int(im.width * ratio)), max(1, int(im.height * ratio))),
                           Image.LANCZOS)
        buf = io.BytesIO()
        if has_alpha:
            im.save(buf, format="PNG", optimize=True)
            mime = "image/png"
        else:
            im.convert("RGB").save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            mime = "image/jpeg"
        data = buf.getvalue()
    except Exception:
        # PIL 이 못 여는 형식이면 원본 그대로 담는다
        data, mime = raw, "image/png"
    return "data:%s;base64,%s" % (mime, base64.b64encode(data).decode("ascii"))


def doc_to_json(doc, indent=2):
    return json.dumps(doc, ensure_ascii=False, indent=indent)


def json_to_doc(raw):
    """업로드한 JSON 을 문서로. 실패하면 (None, 오류메시지)."""
    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
    except Exception as exc:
        return None, "JSON 을 읽을 수 없습니다: %s" % exc
    return schema.normalize(data), None


def load_file(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return schema.normalize(json.load(f))


def save_file(doc, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc_to_json(doc))


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LOCAL_PATH = os.path.join(DATA_DIR, "my_portfolio.json")
DEMO_PATH = os.path.join(DATA_DIR, "demo.json")
LOCAL_MARKER = os.path.join(DATA_DIR, ".local")


def is_local_mode():
    """내 PC 에서 혼자 쓰는 중인가?

    여러 사람이 접속하는 서버에서는 반드시 꺼져 있어야 합니다.
    켜져 있으면 앱이 서버 파일 하나를 읽고 쓰기 때문에,
    한 사람이 저장한 이력을 다른 접속자가 그대로 보게 됩니다.

    두 신호 모두 저장소에 올라가지 않으므로(.gitignore) 배포본에서는 자동으로 꺼집니다.
      - 환경변수 PORTFOLIO_LOCAL=1
      - data/.local 파일 존재
    """
    if os.environ.get("PORTFOLIO_LOCAL", "").strip() == "1":
        return True
    return os.path.exists(LOCAL_MARKER)


def data_uri_bytes(data_uri):
    if not data_uri or "," not in data_uri:
        return None
    try:
        return base64.b64decode(data_uri.split(",", 1)[1])
    except Exception:
        return None
