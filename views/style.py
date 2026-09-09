# -*- coding: utf-8 -*-
"""앱 화면 스타일.

결과물(포트폴리오)과 같은 색·글꼴을 씁니다. 도구와 결과물이 같은 언어를 쓰면
"대충 만든 폼"이 아니라 하나의 제품으로 읽힙니다.

Streamlit 내부 클래스명(st-emotion-cache-…)은 버전마다 바뀌므로 쓰지 않고,
비교적 안정적인 data-testid 만 겨냥합니다.
"""

INK = "#14181d"
BLUE = "#2c5f8a"

# 이름은 여기 한 곳에서만 고치면 화면 전체에 반영됩니다.
BRAND = "취준 포폴 뽀개기_V1"
BRAND_MARK = "취"
BRAND_SUB = "공고에 맞춰 다시 쓰는 포트폴리오"

CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');

:root {
  --ink:#14181d; --ink-2:#1d2329; --line:#e3e8ed; --line-2:#eef1f4;
  --blue:#2c5f8a; --blue-2:#4a90c2; --blue-pale:#eef5fb;
  --muted:#6b7785; --muted-2:#98a2ad;
  --ok:#2c8a5f; --warn:#b4761f; --bad:#c25a4a;
  --radius:10px;
  --shadow:0 1px 2px rgba(20,24,29,.04), 0 6px 20px rgba(20,24,29,.06);
}

html, body, [class*="st-"], button, input, textarea, select {
  font-family:"Pretendard Variable","Pretendard",-apple-system,BlinkMacSystemFont,
              "Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif !important;
}
body { word-break: keep-all; }

/* Streamlit 의 아이콘은 '글꼴이 곧 그림' 입니다. 위에서 글꼴을 강제로 바꾸면
   그림 대신 bolt · lightbulb 같은 이름이 글자로 튀어나오므로 반드시 되돌립니다.
   아이콘 요소 이름이 stIconMaterial 하나가 아니라(stAlertDynamicIcon 등)
   testid 에 Icon 이 들어간 것을 전부 겨냥합니다. 새 이름이 생겨도 안 깨집니다. */
[data-testid*="Icon"], [class*="material-symbols"], [class*="material-icons"] {
  font-family:"Material Symbols Rounded","Material Symbols Outlined" !important;
  font-weight:400 !important; font-style:normal !important;
  letter-spacing:normal !important; text-transform:none !important;
  white-space:nowrap !important; word-break:normal !important;
  direction:ltr !important; -webkit-font-feature-settings:"liga";
  font-feature-settings:"liga"; -webkit-font-smoothing:antialiased;
}
/* 파일 이름·설명이 단어 중간에서 잘리지 않게 */
[data-testid="stCaptionContainer"] p, .stCaption p { word-break:keep-all; }

/* 상단 크롬 정리 — 배포한 앱에 'Deploy' 버튼이 보일 이유가 없다 */
[data-testid="stAppDeployButton"] { display:none; }
[data-testid="stHeader"] { background:transparent; height:0; }
[data-testid="stToolbar"] { right:8px; }
footer { display:none; }

[data-testid="stMainBlockContainer"] { padding-top:2.2rem; max-width:1180px; }

/* ---------------- 사이드바 ---------------- */
[data-testid="stSidebar"] { background:#fbfcfd; border-right:1px solid var(--line); }
[data-testid="stSidebar"] [data-testid="stSidebarNav"] { padding-top:.4rem; }
[data-testid="stSidebar"] a { border-radius:8px !important; font-size:14px !important; }

.brand {
  display:flex; align-items:center; gap:10px; padding:14px 4px 12px;
}
.brand-mark {
  width:34px; height:34px; border-radius:9px; flex:0 0 34px;
  background:linear-gradient(140deg,#2c5f8a,#14181d);
  color:#fff; font-weight:800; font-size:15px;
  display:flex; align-items:center; justify-content:center;
  box-shadow:0 2px 8px rgba(44,95,138,.28);
}
.brand-name { font-weight:800; font-size:15px; color:var(--ink); line-height:1.25; }
.brand-sub { font-size:11.5px; color:var(--muted-2); margin-top:1px; }

.who {
  border:1px solid var(--line); background:#fff; border-radius:var(--radius);
  padding:10px 12px; margin-bottom:2px;
}
.who b { font-size:13.5px; color:var(--ink); }
.who span { display:block; font-size:11.5px; color:var(--muted-2); margin-top:2px; }

/* ---------------- 페이지 머리 ---------------- */
.page-head { margin:0 0 22px; }
.page-eyebrow {
  font-size:11px; font-weight:800; letter-spacing:.14em; text-transform:uppercase;
  color:var(--blue); display:block; margin-bottom:7px;
}
/* Streamlit 기본 h1 이 더 구체적이라 !important 로 눌러야 한다 */
.page-head h1.page-title {
  font-size:27px !important; font-weight:800 !important; letter-spacing:-.02em !important;
  color:var(--ink) !important; margin:0 !important; padding:0 !important; line-height:1.3 !important;
}
.page-sub { font-size:14.5px; color:var(--muted); margin:7px 0 0; line-height:1.6; max-width:760px; }

/* ---------------- 단계 ---------------- */
.step { display:flex; align-items:center; gap:10px; margin:4px 0 10px; }
.step-n {
  width:26px; height:26px; border-radius:50%; flex:0 0 26px;
  display:flex; align-items:center; justify-content:center;
  font-size:12.5px; font-weight:800;
  background:var(--blue-pale); color:var(--blue); border:1px solid #cfe2f2;
}
.step.done .step-n { background:var(--ok); color:#fff; border-color:var(--ok); }
.step-t { font-size:16.5px; font-weight:700; color:var(--ink); }
.step.done .step-t { color:var(--muted); }

/* ---------------- 카드 · 통계 ---------------- */
.stat-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:10px; }
.stat {
  border:1px solid var(--line); background:#fff; border-radius:var(--radius);
  padding:13px 15px;
}
.stat b { display:block; font-size:22px; font-weight:800; color:var(--ink); letter-spacing:-.02em; }
.stat span { display:block; font-size:11.5px; color:var(--muted-2); margin-top:3px; letter-spacing:.02em; }
.stat.hi { background:linear-gradient(150deg,#f6fafe,#fff); border-color:#cfe2f2; }
.stat.hi b { color:var(--blue); }

/* ---------------- 배지 · 알약 ---------------- */
.pill {
  display:inline-block; padding:4px 11px; margin:2px 5px 2px 0; border-radius:999px;
  font-size:12.5px; border:1px solid var(--line); background:#f7f9fb; color:#43505d;
}
.pill.hit { background:var(--blue-pale); border-color:#cfe2f2; color:var(--blue); font-weight:600; }
.pill.miss { background:#fdf3f2; border-color:#f2cfc9; color:var(--bad); font-weight:600; }

/* ---------------- 요구사항 · 조언 ---------------- */
.advice {
  border:1px solid var(--line); border-left:3px solid var(--blue); background:#fbfcfd;
  padding:11px 15px; margin:8px 0; font-size:14px; line-height:1.68;
  border-radius:0 var(--radius) var(--radius) 0; color:#3d4854;
}
.req {
  border:1px solid var(--line); border-left:3px solid var(--line);
  background:#fff; padding:11px 15px; margin:7px 0;
  border-radius:0 var(--radius) var(--radius) 0;
}
.req.ok { border-left-color:var(--ok); background:#fafdfb; }
.req.no { border-left-color:var(--bad); background:#fffbfa; }
.req b { font-size:14.5px; color:var(--ink); }
.req-why { display:block; font-size:13px; color:var(--muted); line-height:1.65; margin-top:4px; }

.fix {
  border:1px solid var(--line); background:#fff; border-radius:var(--radius);
  padding:12px 15px; margin:8px 0; font-size:14px; line-height:1.68; color:#3d4854;
  box-shadow:0 1px 2px rgba(20,24,29,.03);
}
.fix-k {
  display:inline-block; font-size:10.5px; font-weight:800; letter-spacing:.04em;
  color:#fff; background:var(--blue); border-radius:4px; padding:3px 8px; margin-right:9px;
}

/* ---------------- 추천 카드 ---------------- */
.reco {
  border:1px solid var(--line); border-radius:var(--radius); padding:16px 18px;
  margin-bottom:12px; background:#fff; box-shadow:0 1px 2px rgba(20,24,29,.03);
}
.reco .lb {
  font-size:11px; font-weight:800; letter-spacing:.08em; color:var(--blue);
  text-transform:uppercase;
}
.reco .tx {
  font-size:16.5px; font-weight:600; margin:8px 0 9px; white-space:pre-line;
  color:var(--ink); line-height:1.5;
}
.reco .wy { font-size:13px; color:var(--muted); line-height:1.65; }

/* ---------------- 표 ---------------- */
.kw-table { width:100%; border-collapse:collapse; font-size:14px; margin:8px 0 18px; }
.kw-table th {
  text-align:left; font-size:11px; color:var(--muted-2); font-weight:700;
  letter-spacing:.06em; text-transform:uppercase;
  border-bottom:1px solid var(--line); padding:8px 10px;
}
.kw-table td { border-bottom:1px solid var(--line-2); padding:9px 10px; color:#43505d; }
.kw-table .k-w { font-weight:600; color:var(--ink); }
.kw-table .k-kind { color:var(--muted-2); font-size:12.5px; width:62px; }

/* ---------------- 위젯 ---------------- */
.stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button {
  border-radius:8px !important; font-weight:600 !important; font-size:14px !important;
  border-color:var(--line) !important; transition:all .14s ease !important;
}
.stButton button:hover, .stDownloadButton button:hover {
  border-color:var(--blue-2) !important; color:var(--blue) !important;
}
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"] {
  background:var(--blue) !important; border-color:var(--blue) !important; color:#fff !important;
  box-shadow:0 2px 8px rgba(44,95,138,.22) !important;
}
.stButton button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
  background:#24506f !important; color:#fff !important;
}

[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
  border-radius:8px !important; font-size:14px !important;
}
[data-testid="stWidgetLabel"] p { font-size:13px !important; font-weight:600 !important; color:#43505d; }

[data-testid="stExpander"] details {
  border:1px solid var(--line) !important; border-radius:var(--radius) !important;
  background:#fff; box-shadow:0 1px 2px rgba(20,24,29,.03);
}
[data-testid="stExpander"] summary { font-size:14px !important; font-weight:600 !important; }

[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:4px; border-bottom:1px solid var(--line); }
[data-testid="stTabs"] [data-baseweb="tab"] {
  font-size:14px; font-weight:600; padding:9px 14px;
}

[data-testid="stMetric"] {
  border:1px solid var(--line); border-radius:var(--radius); padding:12px 15px; background:#fff;
}
[data-testid="stMetricLabel"] p { font-size:12px !important; color:var(--muted-2) !important; }
[data-testid="stMetricValue"] { font-size:24px !important; font-weight:800 !important; }

[data-testid="stAlert"] { border-radius:var(--radius); font-size:14px; }
hr { margin:1.4rem 0 !important; border-color:var(--line-2) !important; }

/* ---------------- 잠금 화면 ---------------- */
.gate-wrap { max-width:420px; margin:6vh auto 0; text-align:center; }
.gate-mark {
  width:52px; height:52px; border-radius:14px; margin:0 auto 18px;
  background:linear-gradient(140deg,#2c5f8a,#14181d); color:#fff;
  font-size:22px; font-weight:800;
  display:flex; align-items:center; justify-content:center;
  box-shadow:0 6px 20px rgba(44,95,138,.3);
}
.gate-title { font-size:22px; font-weight:800; color:var(--ink); margin:0 0 8px; letter-spacing:-.02em; }
.gate-sub { font-size:14px; color:var(--muted); line-height:1.65; margin:0 0 22px; }
.gate-note { font-size:12px; color:var(--muted-2); margin-top:16px; line-height:1.6; }
</style>
"""
