"""
IAS 19 Local Dashboard

Run from the project root:
    streamlit run src/ias19_dashboard.py
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "output"
RESULTS_FILE = OUTPUT_DIR / "results_ias19.xlsx"

st.set_page_config(page_title="IAS 19 Severance Pay Dashboard", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body { direction: rtl; font-family: 'Inter', sans-serif; background-color: #f8fafc; }
    [data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="block-container"],
    .main,.block-container { direction: rtl; text-align: right; }
    [data-testid="stTabs"] > div:first-child { flex-direction: row-reverse; }
    label,[data-testid="stWidgetLabel"] { direction: rtl; text-align: right; display: block; }
    input,textarea,select { direction: rtl; text-align: right; }
    [data-testid="stMetric"] { direction: rtl; text-align: right; }
    [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 700 !important; }
    [data-testid="stAlert"] { direction: rtl; text-align: right; }
    hr { margin: 20px 0; border-color: #e5e7eb; }
    .kpi-card { background: linear-gradient(135deg,#1e40af 0%,#2563eb 100%); border-radius: 16px;
        padding: 22px 20px; color: white; text-align: center;
        box-shadow: 0 8px 24px rgba(30,64,175,0.25); margin-bottom: 8px; }
    .kpi-card.green  { background: linear-gradient(135deg,#1d4ed8 0%,#38bdf8 100%); }
    .kpi-card.orange { background: linear-gradient(135deg,#b45309 0%,#fbbf24 100%); }
    .kpi-card.red    { background: linear-gradient(135deg,#1e3a8a 0%,#3b82f6 100%); }
    .kpi-card.teal   { background: linear-gradient(135deg,#0284c7 0%,#7dd3fc 100%); }
    .kpi-card.dark   { background: linear-gradient(135deg,#0f172a 0%,#1d4ed8 100%); }
    .kpi-label { font-size: 13px; font-weight: 500; opacity: 0.9; margin-bottom: 6px; }
    .kpi-value { font-size: 28px; font-weight: 700; line-height: 1; }
    .kpi-sub   { font-size: 12px; opacity: 0.75; margin-top: 4px; }
    .emp-card { border-radius: 18px; padding: 20px; margin-bottom: 16px; background: white;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06); border-top: 4px solid #1d4ed8;
        min-height: 340px; direction: rtl; text-align: right; }
    .emp-card.inactive { border-top-color: #9ca3af; }
    .emp-card.female   { border-top-color: #d97706; }
    .emp-avatar { width:52px; height:52px; border-radius:50%; display:flex; align-items:center;
        justify-content:center; font-size:22px; font-weight:700; color:white;
        background:linear-gradient(135deg,#1e40af,#2563eb); margin-bottom:10px; }
    .emp-avatar.female   { background: linear-gradient(135deg,#d97706,#fbbf24); }
    .emp-avatar.inactive { background: linear-gradient(135deg,#6b7280,#9ca3af); }
    .emp-name { font-size:18px; font-weight:700; color:#111827; margin-bottom:2px; }
    .emp-id   { font-size:12px; color:#6b7280; margin-bottom:10px; }
    .badge { display:inline-block; padding:3px 10px; border-radius:999px;
        font-size:11px; font-weight:600; margin-right:4px; }
    .badge-active   { background:#d1fae5; color:#065f46; }
    .badge-inactive { background:#f3f4f6; color:#6b7280; }
    .badge-male     { background:#dbeafe; color:#1e40af; }
    .badge-female   { background:#fef3c7; color:#92400e; }
    .info-grid { display:grid; grid-template-columns:1fr 1fr; gap:6px 12px; margin:10px 0; direction:rtl; }
    .info-item { font-size:13px; text-align:right; }
    .info-label { color:#6b7280; font-weight:500; font-size:11px; }
    .info-value { color:#111827; font-weight:600; }
    .divider-line { height:1px; background:#f3f4f6; margin:12px 0; }
    .liability-box { background:linear-gradient(135deg,#1e40af 0%,#2563eb 100%);
        border-radius:12px; padding:14px; text-align:center; color:white; margin-top:12px; }
    .liability-box.zero { background:linear-gradient(135deg,#6b7280,#9ca3af); }
    .liability-label  { font-size:11px; font-weight:500; opacity:0.85; }
    .liability-amount { font-size:22px; font-weight:700; margin-top:2px; }
    .method-tag { background:#f1f5f9; color:#475569; border-radius:6px;
        padding:2px 8px; font-size:11px; display:inline-block; margin:2px 4px 2px 0; }
    .section-header { font-size:20px; font-weight:700; color:#1f2937;
        border-bottom:3px solid #1d4ed8; padding-bottom:8px;
        margin-bottom:20px; text-align:right; direction:rtl; }
    .page-banner { background:linear-gradient(135deg,#1e40af 0%,#2563eb 100%);
        padding:28px 32px; border-radius:20px; margin-bottom:24px; color:white;
        direction:rtl; text-align:right; }
    .page-banner-title { font-size:30px; font-weight:800; }
    .page-banner-sub   { font-size:15px; opacity:0.85; margin-top:6px; }
    </style>
""", unsafe_allow_html=True)


def fmt_num(value, decimals=2, suffix=""):
    if pd.isna(value):
        return "---"
    try:
        return f"{float(value):,.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def fmt_date(value):
    if pd.isna(value):
        return "---"
    try:
        return pd.to_datetime(value).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(value)


def safe_get(row, col, default=""):
    if col not in row.index:
        return default
    v = row[col]
    return default if pd.isna(v) else v


def is_active(row):
    v = safe_get(row, "Active at Reporting Date", False)
    return str(v).lower() == "true" or v is True


@st.cache_data
def load_results():
    if not RESULTS_FILE.exists():
        return None
    return pd.read_excel(RESULTS_FILE, sheet_name="Employee Results")


def download_bytes():
    with open(RESULTS_FILE, "rb") as f:
        return f.read()


PURPLE = "#1d4ed8"
PINK   = "#d97706"
TEAL   = "#0284c7"
ORANGE = "#f59e0b"


def chart_defaults(fig, height=340):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter", size=12, color="#374151"),
        legend=dict(bgcolor="white", bordercolor="#e5e7eb", borderwidth=1),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#f3f4f6", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f3f4f6", zeroline=False)
    return fig


def render_employee_card(row):
    gender     = str(safe_get(row, "Gender", "M")).upper()
    active     = is_active(row)
    first_name = safe_get(row, "First Name", "---")
    last_name  = safe_get(row, "Last Name", "---")
    emp_id     = safe_get(row, "Employee ID", "---")
    salary     = safe_get(row, "Salary", 0)
    plan_asset = safe_get(row, "Plan Asset", 0)
    deposits   = safe_get(row, "Deposits", 0)
    s14_pct    = safe_get(row, "Section 14 Percent", 0)
    s14_factor = safe_get(row, "Section 14 Calculation Factor", 0)
    liability  = safe_get(row, "IAS19 Liability", 0)
    age        = safe_get(row, "Age at Valuation", 0)
    service    = safe_get(row, "Service at Valuation", 0)
    ret_age    = safe_get(row, "Retirement Age Used", "---")
    birth_date = safe_get(row, "Birth Date")
    start_date = safe_get(row, "Start Date")
    term_date  = safe_get(row, "Termination Date")
    term_rsn   = safe_get(row, "Termination Reason", "---")
    ret_meth   = safe_get(row, "Effective Retirement Method", "---")
    sal_meth   = safe_get(row, "Effective Salary Method", "---")
    dis_meth   = safe_get(row, "Effective Discount Method", "---")

    initials = (str(first_name)[0] + str(last_name)[0]).upper() if first_name and last_name else "?"
    card_cls   = "emp-card" + ("" if active else " inactive") + (" female" if gender == "F" else "")
    avatar_cls = "emp-avatar" + (" female" if gender == "F" else "") + ("" if active else " inactive")
    g_badge = "<span class='badge badge-female'>נקבה</span>" if gender == "F" else "<span class='badge badge-male'>זכר</span>"
    s_badge = "<span class='badge badge-active'>פעיל/ה</span>" if active else "<span class='badge badge-inactive'>לא פעיל/ה</span>"
    liab_cls = "liability-box" if float(liability or 0) > 0 else "liability-box zero"
    ils = "&#x20AA;"

    html = f"""
    <div class="{card_cls}">
      <div class="{avatar_cls}">{initials}</div>
      <div class="emp-name">{first_name} {last_name}</div>
      <div class="emp-id">מספר עובד: {emp_id} &nbsp; {g_badge} {s_badge}</div>
      <div class="info-grid">
        <div class="info-item"><div class="info-label">תאריך לידה</div><div class="info-value">{fmt_date(birth_date)}</div></div>
        <div class="info-item"><div class="info-label">גיל בתאריך הערכה</div><div class="info-value">{fmt_num(age, 1)} שנים</div></div>
        <div class="info-item"><div class="info-label">תאריך תחילת עבודה</div><div class="info-value">{fmt_date(start_date)}</div></div>
        <div class="info-item"><div class="info-label">ותק בתאריך הערכה</div><div class="info-value">{fmt_num(service, 1)} שנים</div></div>
        <div class="info-item"><div class="info-label">תאריך סיום</div><div class="info-value">{fmt_date(term_date)}</div></div>
        <div class="info-item"><div class="info-label">סיבת סיום</div><div class="info-value">{term_rsn}</div></div>
      </div>
      <div class="divider-line"></div>
      <div class="info-grid">
        <div class="info-item"><div class="info-label">שכר</div><div class="info-value">{ils}{fmt_num(salary, 0)}</div></div>
        <div class="info-item"><div class="info-label">נכסי קרן</div><div class="info-value">{ils}{fmt_num(plan_asset, 0)}</div></div>
        <div class="info-item"><div class="info-label">הפקדות</div><div class="info-value">{ils}{fmt_num(deposits, 0)}</div></div>
        <div class="info-item"><div class="info-label">אחוז סעיף 14</div><div class="info-value">{fmt_num(s14_pct, 0)}%</div></div>
        <div class="info-item"><div class="info-label">גיל פרישה</div><div class="info-value">{ret_age}</div></div>
        <div class="info-item"><div class="info-label">מקדם סעיף 14</div><div class="info-value">{fmt_num(s14_factor, 3)}</div></div>
      </div>
      <div class="divider-line"></div>
      <div style="font-size:11px;color:#6b7280;margin-bottom:6px;text-align:right;">מודל חישוב:</div>
      <span class="method-tag">{ret_meth}</span>
      <span class="method-tag">{sal_meth}</span>
      <span class="method-tag">{dis_meth}</span>
      <div class="{liab_cls}">
        <div class="liability-label">IAS 19 LIABILITY</div>
        <div class="liability-amount">{ils}{fmt_num(liability, 0)}</div>
      </div>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)


# ── Main ──

st.markdown("""
<div class="page-banner">
  <div class="page-banner-title">IAS 19 &mdash; מערכת הערכת פיצויי פרישה</div>
  <div class="page-banner-sub">ניהול ועיבוד נתוני פיצויים לפי תקן IAS 19 &mdash; תאריך הערכה: 31/12/2023</div>
</div>""", unsafe_allow_html=True)

df = load_results()
if df is None:
    st.error("לא נמצא הקובץ output/results_ias19.xlsx. יש להריץ תחילה את src/ias19_project.py.")
    st.stop()
if "IAS19 Liability" not in df.columns:
    st.error("הקובץ אינו מכיל עמודת IAS19 Liability.")
    st.stop()

total_liability   = df["IAS19 Liability"].sum()
employee_count    = len(df)
active_mask       = df["Active at Reporting Date"].astype(str).str.lower() == "true"
active_count      = int(active_mask.sum())
total_plan_assets = df["Plan Asset"].sum() if "Plan Asset" in df.columns else 0
avg_liability     = df.loc[df["IAS19 Liability"] > 0, "IAS19 Liability"].mean()
total_deposits    = df["Deposits"].sum() if "Deposits" in df.columns else 0
net_liability     = total_liability - total_plan_assets
ils = "&#x20AA;"

c1, c2, c3, c4, c5, c6 = st.columns(6)
kpis = [
    (c1, "purple", 'סה"כ עובדים',         f"{employee_count:,}",              f"{active_count:,} פעילים"),
    (c2, "green",  "התחייבות כוללת IAS 19", f"{ils}{total_liability:,.0f}",    "Present Value"),
    (c3, "teal",   "נכסי קרן כוללים",       f"{ils}{total_plan_assets:,.0f}",  "Plan Assets"),
    (c4, "orange", "התחייבות נטו",           f"{ils}{net_liability:,.0f}",      "Liability minus Assets"),
    (c5, "red",    "התחייבות ממוצעת",        f"{ils}{avg_liability:,.0f}",      "לעובד עם התחייבות"),
    (c6, "dark",   'סה"כ הפקדות',           f"{ils}{total_deposits:,.0f}",     "הפקדות שנתיות"),
]
for col, color, label, value, sub in kpis:
    with col:
        st.markdown(f"""<div class="kpi-card {color}">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-sub">{sub}</div></div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
dl_col, _ = st.columns([1, 4])
with dl_col:
    st.download_button(
        label="הורד קובץ Excel מלא",
        data=download_bytes(),
        file_name="results_ias19.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
st.divider()

tab_charts, tab_cards, tab_table = st.tabs(["תרשימים וניתוח", "כרטיסי עובד", "טבלה מלאה"])

# ── TAB 1 – Charts ──
with tab_charts:
    r1a, r1b = st.columns([2, 1])
    with r1a:
        st.markdown('<div class="section-header">התפלגות התחייבות IAS 19</div>', unsafe_allow_html=True)
        plot_df = df[df["IAS19 Liability"] > 0].copy()
        plot_df["שם"] = plot_df["First Name"] + " " + plot_df["Last Name"]
        plot_df = plot_df.sort_values("IAS19 Liability", ascending=False)
        fig = px.bar(plot_df, x="שם", y="IAS19 Liability", color="Gender",
            color_discrete_map={"M": PURPLE, "F": PINK},
            labels={"IAS19 Liability": "התחייבות (ILS)", "שם": "עובד", "Gender": "מגדר"},
            text=plot_df["IAS19 Liability"].apply(lambda v: f"{v:,.0f}"))
        fig.update_traces(textposition="outside", textfont_size=10)
        chart_defaults(fig, 360)
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)
    with r1b:
        st.markdown('<div class="section-header">פילוח מגדרי</div>', unsafe_allow_html=True)
        gc = df["Gender"].value_counts().reset_index()
        gc.columns = ["מגדר", "עובדים"]
        gc["מגדר"] = gc["מגדר"].map({"M": "זכר", "F": "נקבה"})
        fig2 = px.pie(gc, names="מגדר", values="עובדים", color="מגדר",
            color_discrete_map={"זכר": PURPLE, "נקבה": PINK}, hole=0.5)
        fig2.update_traces(textinfo="label+percent+value", textfont_size=13)
        chart_defaults(fig2, 360)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    r2a, r2b = st.columns(2)
    with r2a:
        st.markdown('<div class="section-header">התפלגות גיל בתאריך הערכה</div>', unsafe_allow_html=True)
        fig3 = px.histogram(df, x="Age at Valuation", color="Gender", nbins=18,
            color_discrete_map={"M": PURPLE, "F": PINK}, barmode="overlay", opacity=0.75,
            labels={"Age at Valuation": "גיל", "count": "מספר עובדים", "Gender": "מגדר"})
        chart_defaults(fig3, 320)
        st.plotly_chart(fig3, use_container_width=True)
    with r2b:
        st.markdown('<div class="section-header">התפלגות ותק בתאריך הערכה</div>', unsafe_allow_html=True)
        fig4 = px.histogram(df, x="Service at Valuation", color="Gender", nbins=15,
            color_discrete_map={"M": PURPLE, "F": PINK}, barmode="overlay", opacity=0.75,
            labels={"Service at Valuation": "ותק (שנים)", "count": "מספר עובדים", "Gender": "מגדר"})
        chart_defaults(fig4, 320)
        st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    r3a, r3b = st.columns([3, 2])
    with r3a:
        st.markdown('<div class="section-header">שכר מול התחייבות IAS 19</div>', unsafe_allow_html=True)
        sdf = df.copy()
        sdf["שם"] = sdf["First Name"] + " " + sdf["Last Name"]
        sdf["מגדר"] = sdf["Gender"].map({"M": "זכר", "F": "נקבה"})
        fig5 = px.scatter(sdf, x="Salary", y="IAS19 Liability", color="מגדר",
            size="Service at Valuation", hover_name="שם",
            hover_data={"Salary": ":,.0f", "IAS19 Liability": ":,.0f",
                        "Age at Valuation": ":.1f", "Service at Valuation": ":.1f"},
            color_discrete_map={"זכר": PURPLE, "נקבה": PINK},
            labels={"Salary": "שכר (ILS)", "IAS19 Liability": "התחייבות IAS 19 (ILS)"}, size_max=22)
        chart_defaults(fig5, 360)
        st.plotly_chart(fig5, use_container_width=True)
    with r3b:
        st.markdown('<div class="section-header">שיטות חישוב - פרישה</div>', unsafe_allow_html=True)
        if "Effective Retirement Method" in df.columns:
            mc = df["Effective Retirement Method"].value_counts().reset_index()
            mc.columns = ["שיטה", "עובדים"]
            fig6 = px.pie(mc, names="שיטה", values="עובדים", hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Pastel)
            fig6.update_traces(textinfo="label+percent", textfont_size=11)
            chart_defaults(fig6, 360)
            st.plotly_chart(fig6, use_container_width=True)

    st.divider()
    st.markdown('<div class="section-header">מבט פיננסי מצטבר</div>', unsafe_allow_html=True)
    wlabels = ['סה"כ שכר שנתי', 'סה"כ הפקדות', "נכסי קרן", "התחייבות IAS 19"]
    wvals = [df["Salary"].sum(), df["Deposits"].sum(), df["Plan Asset"].sum(), df["IAS19 Liability"].sum()]
    fig7 = go.Figure(go.Bar(x=wlabels, y=wvals, marker_color=[PURPLE, TEAL, ORANGE, "#ef4444"],
        text=[f"{v:,.0f}" for v in wvals], textposition="outside"))
    chart_defaults(fig7, 360)
    fig7.update_layout(showlegend=False)
    st.plotly_chart(fig7, use_container_width=True)

    st.divider()
    st.markdown('<div class="section-header">התחייבות לפי קבוצות גיל</div>', unsafe_allow_html=True)
    adf = df.copy()
    adf["קבוצת גיל"] = pd.cut(adf["Age at Valuation"], [0, 30, 40, 50, 60, 70, 999],
        labels=["עד 30", "31-40", "41-50", "51-60", "61-70", "70+"], right=False)
    agg = adf.groupby("קבוצת גיל", observed=True)["IAS19 Liability"].agg(["sum", "mean", "count"]).reset_index()
    agg.columns = ["קבוצת גיל", 'סה"כ התחייבות', "ממוצע לעובד", "מספר עובדים"]
    fig8 = make_subplots(specs=[[{"secondary_y": True}]])
    fig8.add_trace(go.Bar(x=agg["קבוצת גיל"], y=agg['סה"כ התחייבות'],
        name='סה"כ התחייבות', marker_color=PURPLE,
        text=agg['סה"כ התחייבות'].apply(lambda v: f"{v:,.0f}"), textposition="outside"), secondary_y=False)
    fig8.add_trace(go.Scatter(x=agg["קבוצת גיל"], y=agg["ממוצע לעובד"],
        name="ממוצע לעובד", mode="lines+markers", marker_color=ORANGE, line_width=2), secondary_y=True)
    fig8.update_yaxes(title_text='סה"כ התחייבות (ILS)', secondary_y=False)
    fig8.update_yaxes(title_text="ממוצע לעובד (ILS)", secondary_y=True)
    chart_defaults(fig8, 360)
    fig8.update_layout(legend=dict(x=0.01, y=0.99))
    st.plotly_chart(fig8, use_container_width=True)

    st.divider()
    st.markdown('<div class="section-header">נכסי קרן מול התחייבות - לפי עובד</div>', unsafe_allow_html=True)
    cdf = df.copy()
    cdf["שם"] = cdf["First Name"] + " " + cdf["Last Name"]
    cdf = cdf.sort_values("IAS19 Liability", ascending=False)
    fig9 = go.Figure()
    fig9.add_trace(go.Bar(name="התחייבות IAS 19", x=cdf["שם"], y=cdf["IAS19 Liability"], marker_color=PURPLE))
    fig9.add_trace(go.Bar(name="נכסי קרן", x=cdf["שם"], y=cdf["Plan Asset"], marker_color=TEAL))
    fig9.update_layout(barmode="group")
    chart_defaults(fig9, 380)
    fig9.update_xaxes(tickangle=-30)
    st.plotly_chart(fig9, use_container_width=True)

# ── TAB 2 – Employee Cards ──
with tab_cards:
    st.markdown('<div class="section-header">חיפוש וסינון</div>', unsafe_allow_html=True)
    fc1, fc2, fc3, fc4 = st.columns([3, 1, 1, 1])
    with fc1:
        search_text = st.text_input("חיפוש לפי שם או מספר עובד", "")
    with fc2:
        gopts = (["הכל"] + sorted(df["Gender"].dropna().astype(str).unique().tolist())
                 if "Gender" in df.columns else ["הכל"])
        sel_gender = st.selectbox("מגדר", gopts)
    with fc3:
        sel_status = st.selectbox("סטטוס", ["הכל", "פעיל/ה", "לא פעיל/ה"])
    with fc4:
        sort_opts = ["התחייבות - גבוה לנמוך", "התחייבות - נמוך לגבוה",
                     "שם א-ת", "גיל - גבוה לנמוך", "ותק - גבוה לנמוך"]
        sort_by = st.selectbox("מיון", sort_opts)

    fdf = df.copy()
    if search_text.strip():
        s = search_text.strip().lower()
        mask = (fdf["Employee ID"].astype(str).str.lower().str.contains(s, na=False)
              | fdf["First Name"].astype(str).str.lower().str.contains(s, na=False)
              | fdf["Last Name"].astype(str).str.lower().str.contains(s, na=False))
        fdf = fdf[mask]
    if sel_gender != "הכל" and "Gender" in fdf.columns:
        fdf = fdf[fdf["Gender"].astype(str) == sel_gender]
    if sel_status != "הכל" and "Active at Reporting Date" in fdf.columns:
        if sel_status == "פעיל/ה":
            fdf = fdf[fdf["Active at Reporting Date"].astype(str).str.lower() == "true"]
        else:
            fdf = fdf[fdf["Active at Reporting Date"].astype(str).str.lower() != "true"]
    smap = {
        "התחייבות - גבוה לנמוך": ("IAS19 Liability", False),
        "התחייבות - נמוך לגבוה": ("IAS19 Liability", True),
        "שם א-ת":                 ("First Name", True),
        "גיל - גבוה לנמוך":      ("Age at Valuation", False),
        "ותק - גבוה לנמוך":      ("Service at Valuation", False),
    }
    scol, sasc = smap[sort_by]
    if scol in fdf.columns:
        fdf = fdf.sort_values(scol, ascending=sasc)

    st.markdown(
        f'<div style="color:#6b7280;font-size:14px;margin-bottom:16px;'
        f'text-align:right;direction:rtl;">מציג <b>{len(fdf)}</b> עובדים</div>',
        unsafe_allow_html=True,
    )
    for rg in [fdf.iloc[i:i + 3] for i in range(0, len(fdf), 3)]:
        cols = st.columns(3)
        for col, (_, er) in zip(cols, rg.iterrows()):
            with col:
                render_employee_card(er)

# ── TAB 3 – Full Table ──
with tab_table:
    st.markdown('<div class="section-header">טבלת נתונים מלאה</div>', unsafe_allow_html=True)
    ddf = df.copy()
    for c in ["Birth Date", "Start Date", "Section 14 Date", "Termination Date"]:
        if c in ddf.columns:
            ddf[c] = ddf[c].apply(fmt_date)
    for c in ["Salary", "Plan Asset", "Deposits", "IAS19 Liability"]:
        if c in ddf.columns:
            ddf[c] = ddf[c].apply(lambda v: fmt_num(v, 0))
    for c in ["Age at Valuation", "Service at Valuation",
              "Section 14 Percent", "Section 14 Calculation Factor"]:
        if c in ddf.columns:
            ddf[c] = ddf[c].apply(lambda v: fmt_num(v, 2))
    if "Gender" in ddf.columns:
        ddf["Gender"] = ddf["Gender"].map({"M": "זכר", "F": "נקבה"})
    if "Active at Reporting Date" in ddf.columns:
        ddf["Active at Reporting Date"] = ddf["Active at Reporting Date"].apply(
            lambda v: "פעיל/ה" if str(v).lower() == "true" else "לא פעיל/ה")
    rn = {
        "Employee ID": "מזהה", "First Name": "שם פרטי", "Last Name": "שם משפחה",
        "Gender": "מגדר", "Birth Date": "תאריך לידה", "Start Date": "תאריך תחילה",
        "Salary": "שכר", "Section 14 Date": "תאריך סעיף 14",
        "Section 14 Percent": "אחוז סעיף 14", "Plan Asset": "נכסי קרן",
        "Deposits": "הפקדות", "Termination Date": "תאריך סיום",
        "Termination Reason": "סיבת סיום", "Age at Valuation": "גיל (שנים)",
        "Service at Valuation": "ותק (שנים)", "Retirement Age Used": "גיל פרישה",
        "Active at Reporting Date": "סטטוס", "Section 14 Calculation Factor": "מקדם סעיף 14",
        "Effective Retirement Method": "שיטת פרישה", "Effective Salary Method": "שיטת שכר",
        "Effective Discount Method": "שיטת היוון", "Effective Project Asset": "הקרנת נכס",
        "Effective Project Deposits": "הקרנת הפקדות", "IAS19 Liability": "התחייבות IAS19",
    }
    ddf.rename(columns={k: v for k, v in rn.items() if k in ddf.columns}, inplace=True)
    st.dataframe(ddf, use_container_width=True, height=540)
    dl2, _ = st.columns([1, 5])
    with dl2:
        st.download_button(
            label="הורד Excel",
            data=download_bytes(),
            file_name="results_ias19.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )