"""CSM 客戶成功儀表板

多客戶管理視角：組合層指標（ARR / NRR / GRR / NPS / CSAT / 採用率）＋
單一客戶的生命週期細節（導入里程碑、QBR、續約進度、Champion 地圖）。

⚠️ 展示模式的資料全為虛構，不含任何真實客戶資訊。
"""

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import advice
import demo_data
import scoring

st.set_page_config(page_title="CSM 客戶成功儀表板", page_icon="◈", layout="wide")

# ---------------------------------------------------------------- 樣式

C = {
    "bg": "#0F1B2D", "card": "#1A2E4A", "line": "#2A4F7A",
    "text": "#E2E8F0", "muted": "#94A3B8", "dim": "#64748B",
    "green": "#00D4AA", "yellow": "#F59E0B", "red": "#EF4444",
    "blue": "#3B82F6", "indigo": "#6366F1",
}

TIER_COLOR = {"green": C["green"], "yellow": C["yellow"], "red": C["red"]}
TIER_TEXT = {"green": "健康", "yellow": "注意", "red": "高風險"}

STAGE_COLOR = {
    "導入": C["indigo"], "採用": C["green"], "成熟": C["blue"],
    "續約中": C["yellow"], "已流失": C["dim"],
}
STAGE_ORDER = ["導入", "採用", "成熟", "續約中"]

RENEWAL_STAGES = ["未啟動", "需求確認", "提案已送", "議價中", "已簽回"]

st.markdown(f"""
<style>
  .block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1500px; }}
  .kpi {{ background:{C['card']}; border:1px solid {C['line']}; border-radius:12px;
         padding:14px 16px; height:100%; }}
  .kpi .lbl {{ font-size:11px; color:{C['muted']}; letter-spacing:.06em; margin-bottom:6px; }}
  .kpi .val {{ font-size:25px; font-weight:700; line-height:1.15; font-variant-numeric:tabular-nums; }}
  .kpi .sub {{ font-size:11px; color:{C['dim']}; margin-top:5px; }}
  .pill {{ display:inline-block; font-size:11px; padding:2px 9px; border-radius:6px;
           font-weight:600; white-space:nowrap; }}
  .tag {{ display:inline-block; font-size:11px; padding:2px 9px; border-radius:20px;
          border:1px solid {C['line']}; color:{C['muted']}; margin-right:5px; }}
  .panel {{ background:{C['card']}; border:1px solid {C['line']}; border-radius:12px; padding:16px 18px; }}
  .sect {{ font-size:15px; font-weight:700; margin:6px 0 12px; }}
  .row-title {{ font-size:14px; font-weight:600; color:{C['text']}; }}
  .row-sub {{ font-size:11px; color:{C['dim']}; }}
  .bar-bg {{ height:5px; background:{C['bg']}; border-radius:3px; overflow:hidden; }}
  .mile {{ display:flex; gap:10px; padding:9px 0; border-bottom:1px solid {C['bg']}; align-items:flex-start; }}
  .num {{ font-variant-numeric:tabular-nums; }}
  div[data-testid="stMetricValue"] {{ font-size:22px; }}
  section[data-testid="stSidebar"] {{ border-right:1px solid {C['line']}; }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- 小元件

def fmt_money(v):
    if v is None:
        return "—"
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 10000:
        return f"{sign}NT${v/10000:,.0f}萬"
    return f"{sign}NT${v:,.0f}"


def fmt_pct(v, digits=1):
    return "—" if v is None else f"{v:.{digits}f}%"


def fmt_num(v, suffix="", digits=1):
    """缺資料時顯示破折號，而不是 None。上傳模式的 CSV 常常少欄位。"""
    if v is None:
        return "—"
    return f"{v:.{digits}f}{suffix}" if isinstance(v, float) else f"{v}{suffix}"


def fmt_nps(v):
    if v is None:
        return "—"
    return f"+{v}" if v > 0 else str(v)


def md_safe(text):
    """Streamlit 的 markdown 會把成對的 $ 當成 LaTeX，純文字區塊要先跳脫。"""
    return text.replace("$", r"\$")


def kpi(label, value, sub="", accent=None):
    color = accent or C["text"]
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return (f'<div class="kpi"><div class="lbl">{label}</div>'
            f'<div class="val" style="color:{color}">{value}</div>{sub_html}</div>')


def kpi_row(items):
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        col.markdown(kpi(*item[:3], accent=item[3] if len(item) > 3 else None),
                     unsafe_allow_html=True)


def pill(text, color):
    return f'<span class="pill" style="background:{color}22;color:{color}">{text}</span>'


def health_ring(value, color, size=54):
    r = (size - 7) / 2
    circ = 2 * 3.14159 * r
    fill = max(value, 0) / 100 * circ
    fs = round(size * 0.30)
    return (
        f'<div style="position:relative;width:{size}px;height:{size}px">'
        f'<svg width="{size}" height="{size}" style="transform:rotate(-90deg)">'
        f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{C["line"]}" stroke-width="5"/>'
        f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{color}" stroke-width="5"'
        f' stroke-dasharray="{fill:.1f} {circ:.1f}" stroke-linecap="round"/></svg>'
        f'<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;'
        f'font-size:{fs}px;font-weight:700;color:{color}">{value:.0f}</div></div>'
    )


def progress_bar(pct, color):
    pct = max(0, min(100, pct or 0))
    return (f'<div class="bar-bg"><div style="height:100%;width:{pct}%;'
            f'background:{color};border-radius:3px"></div></div>')


def dark_fig(fig, height=260):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=C["muted"], size=12), height=height,
        margin=dict(l=8, r=8, t=28, b=8), showlegend=False,
        xaxis=dict(gridcolor=C["line"], zerolinecolor=C["line"]),
        yaxis=dict(gridcolor=C["line"], zerolinecolor=C["line"]),
    )
    return fig


# ---------------------------------------------------------------- 資料載入

@st.cache_data
def load_demo(today_iso):
    return demo_data.load_customers(date.fromisoformat(today_iso))


UPLOAD_ALIASES = {
    "客戶名稱": "name", "方案": "plan", "生命週期階段": "stage", "負責CSM": "csm",
    "產業": "industry", "上期ARR": "prev_arr", "本期ARR": "arr", "合約金額": "arr",
    "合約到期日": "renewal_date", "已購席位": "seats_purchased", "活躍席位": "seats_active",
    "近30天使用次數": "usage_30d", "近90天客服工單數": "tickets_90d",
    "近90天緊急工單數": "urgent_tickets_90d", "導入完成度(%)": "onboarding_pct",
    "NPS推薦分數(0-10)": "nps", "滿意度分數(NPS/CSAT)": "nps", "CSAT(1-5)": "csat",
    "距今最近互動天數": "last_contact_days",
}

NUMERIC_FIELDS = ["prev_arr", "arr", "seats_purchased", "seats_active", "usage_30d",
                  "tickets_90d", "urgent_tickets_90d", "onboarding_pct", "nps", "csat",
                  "last_contact_days"]


def parse_upload(df, today):
    if "客戶名稱" not in df.columns or "合約到期日" not in df.columns:
        raise ValueError("CSV 至少需要「客戶名稱」與「合約到期日」兩個欄位。")

    customers = []
    for i, row in df.iterrows():
        c = {"id": f"u{i:03d}", "status": "active", "stage": "成熟", "plan": "-",
             "csm": "-", "industry": "-", "tags": [], "milestones": [], "meetings": [],
             "contacts": [], "renewal": {}, "prev_arr": 0, "ttv_days": None}
        for col, key in UPLOAD_ALIASES.items():
            if col in df.columns and pd.notna(row[col]):
                c[key] = row[col]
        for key in NUMERIC_FIELDS:
            if key in c and c[key] is not None:
                try:
                    c[key] = float(c[key])
                except (TypeError, ValueError):
                    c[key] = None
        c["name"] = str(c["name"])
        renewal = pd.to_datetime(c["renewal_date"]).date()
        c["renewal_date"] = renewal.isoformat()
        c["renewal_in_days"] = (renewal - today).days
        c["renewal"] = {"stage": "未啟動", "amount": c.get("arr") or 0, "expansion": 0,
                        "probability": None, "next_action": None,
                        "next_action_in_days": None, "note": ""}
        customers.append(c)
    return customers


# ---------------------------------------------------------------- 側邊欄

TODAY = date.today()

st.sidebar.markdown(
    f'<div style="padding:2px 0 14px">'
    f'<div style="font-size:11px;color:{C["green"]};letter-spacing:.15em;font-weight:700">CSM PLATFORM</div>'
    f'<div style="font-size:18px;font-weight:700;margin-top:2px">客戶成功儀表板</div></div>',
    unsafe_allow_html=True)

mode = st.sidebar.radio("資料來源", ["展示模式（內建虛構資料）", "上傳模式（自己的 CSV）"],
                        label_visibility="collapsed")
IS_DEMO = mode.startswith("展示")

raw_customers, upload_error = None, None
if IS_DEMO:
    raw_customers = load_demo(TODAY.isoformat())
else:
    st.sidebar.caption("上傳 CSV 後即可算出健康分數與收入指標；導入／QBR／續約／聯絡人等細節僅展示模式提供。")
    up = st.sidebar.file_uploader("上傳客戶資料 CSV", type=["csv"])
    if up:
        try:
            raw_customers = parse_upload(pd.read_csv(up), TODAY)
        except Exception as e:
            upload_error = str(e)

if raw_customers is None:
    st.title("CSM 客戶成功儀表板")
    if upload_error:
        st.error(f"讀取 CSV 發生問題：{upload_error}")
    st.info("請在左側上傳 CSV，或切換回「展示模式」直接查看完整儀表板。")
    with st.expander("CSV 欄位範本"):
        st.code(",".join(UPLOAD_ALIASES.keys()), language=None)
        st.caption("「客戶名稱」與「合約到期日」為必填，其餘欄位缺少時會自動把權重分配給其他構面。")
    st.stop()

customers = scoring.enrich(raw_customers, TODAY)
by_id = {c["id"]: c for c in customers}

PAGES = ["總覽", "客戶列表", "客戶詳情", "續約管理", "指標字典"]

if "nav" not in st.session_state:
    st.session_state.nav = "總覽"
if "selected_id" not in st.session_state:
    st.session_state.selected_id = customers[0]["id"]
if "table_nonce" not in st.session_state:
    st.session_state.table_nonce = 0

# 程式化換頁只能在 radio 這個 widget 被建立「之前」寫入它的 key，
# 所以改用待跳轉旗標，由下一次 rerun 在此處套用。
if st.session_state.get("_pending_nav"):
    st.session_state.nav = st.session_state.pop("_pending_nav")

st.sidebar.radio("頁面", PAGES, key="nav")

csm_options = ["全部"] + sorted({c["csm"] for c in customers if c["csm"] != "-"})
csm_filter = st.sidebar.selectbox("負責 CSM", csm_options)

st.sidebar.divider()
api_key = advice.get_api_key()
use_ai = st.sidebar.toggle(
    "用 Claude 生成風險說明", value=False, disabled=not api_key,
    help="需設定 ANTHROPIC_API_KEY。未設定時使用內建規則引擎（同樣可正常運作）。")
if not api_key:
    st.sidebar.caption("未偵測到 ANTHROPIC_API_KEY，目前使用規則引擎生成建議。")

if IS_DEMO:
    st.sidebar.caption("⚠️ 展示模式資料全為虛構，不含任何真實客戶資訊。")


def scoped(cs):
    return cs if csm_filter == "全部" else [c for c in cs if c["csm"] == csm_filter]


view = scoped(customers)
active = [c for c in view if c["status"] == "active"]
metrics = scoring.portfolio_metrics(view)
actions = scoring.build_action_items(view, TODAY)


def goto_detail(cid):
    st.session_state.selected_id = cid
    st.session_state._pending_nav = "客戶詳情"
    st.session_state.table_nonce += 1
    st.rerun()


# ---------------------------------------------------------------- 頁面：總覽

def page_overview():
    st.markdown("### 儀表板總覽")
    urgent_n = len([a for a in actions if a["urgent"]])
    st.caption(f"{TODAY.strftime('%Y 年 %m 月 %d 日')}　·　"
               f"{metrics['customer_count']} 個有效客戶　·　"
               f"{urgent_n} 項待辦已逾期或需本週處理")

    st.write("")
    kpi_row([
        ("年度經常性收入 ARR", fmt_money(metrics["arr"]),
         f"{metrics['customer_count']} 個有效合約", C["green"]),
        ("淨收入留存率 NRR", fmt_pct(metrics["nrr"]),
         f"擴展 {fmt_money(metrics['expansion'])}",
         C["green"] if (metrics["nrr"] or 0) >= 100 else C["yellow"]),
        ("總收入留存率 GRR", fmt_pct(metrics["grr"]),
         f"流失 {fmt_money(metrics['churn_arr'])}",
         C["green"] if (metrics["grr"] or 0) >= 90 else C["yellow"]),
        ("客戶留存率", fmt_pct(metrics["logo_retention"]),
         f"期內流失 {metrics['churned_count']} 家",
         C["green"] if (metrics["logo_retention"] or 0) >= 90 else C["yellow"]),
        ("90 天內到期 ARR", fmt_money(metrics["renewing_arr"]),
         f"{metrics['renewing_count']} 家待續約", C["yellow"]),
    ])
    st.write("")
    kpi_row([
        ("平均健康分數", fmt_num(metrics["avg_health"]), "滿分 100",
         C["green"] if (metrics["avg_health"] or 0) >= 70 else C["yellow"]),
        ("高風險客戶", f"{metrics['at_risk']}",
         f"另有 {metrics['watch']} 家黃燈需注意", C["red"]),
        ("NPS", fmt_nps(metrics["nps"]),
         f"促進者 {metrics['nps_promoters']}／批評者 {metrics['nps_detractors']}（共 {metrics['nps_respondents']} 份）",
         C["green"] if (metrics["nps"] or 0) >= 30 else C["yellow"]),
        ("CSAT", f"{metrics['csat']} / 5" if metrics["csat"] else "—", "近 90 天平均滿意度",
         C["green"] if (metrics["csat"] or 0) >= 4 else C["yellow"]),
        ("席位採用率", fmt_pct(metrics["seat_rate"]),
         f"閒置 {metrics['idle_seats']:,} 席　·　平均 TTV {fmt_num(metrics['avg_ttv'], ' 天')}",
         C["green"] if (metrics["seat_rate"] or 0) >= 70 else C["yellow"]),
    ])

    st.write("")
    left, right = st.columns([3, 2])

    with left:
        st.markdown('<div class="sect">ARR 變動橋接圖（本期 vs 上期）</div>', unsafe_allow_html=True)
        if not metrics["start_arr"]:
            st.info("上傳的 CSV 沒有「上期ARR」欄位，因此無法計算 NRR／GRR 與 ARR 變動。\n\n"
                    "留存率比較的是**同一批客戶在兩個時間點**的差異，"
                    "單一時間點的快照算不出來 —— 補上「上期ARR」欄位即可。")
        else:
            fig = go.Figure(go.Waterfall(
                orientation="v",
                measure=["absolute", "relative", "relative", "relative", "total"],
                x=["期初 ARR", "擴展", "縮減", "流失", "期末 ARR"],
                y=[metrics["start_arr"], metrics["expansion"],
                   -metrics["contraction"], -metrics["churn_arr"], 0],
                text=[fmt_money(metrics["start_arr"]), f"+{fmt_money(metrics['expansion'])}",
                      f"-{fmt_money(metrics['contraction'])}", f"-{fmt_money(metrics['churn_arr'])}",
                      fmt_money(metrics["end_arr"])],
                textposition="outside",
                connector=dict(line=dict(color=C["line"])),
                increasing=dict(marker=dict(color=C["green"])),
                decreasing=dict(marker=dict(color=C["red"])),
                totals=dict(marker=dict(color=C["blue"])),
            ))
            st.plotly_chart(dark_fig(fig, 300), width="stretch")
            st.caption(md_safe(
                f"只計入上期就存在的客戶（{fmt_money(metrics['start_arr'])}），本期新簽不列入 —— "
                f"這正是 NRR {fmt_pct(metrics['nrr'])} 的算法。"))

    with right:
        st.markdown('<div class="sect">生命週期分佈</div>', unsafe_allow_html=True)
        counts = [(s, len([c for c in active if c["stage"] == s]),
                   sum(c["arr"] for c in active if c["stage"] == s)) for s in STAGE_ORDER]
        for stage, n, arr in counts:
            share = n / len(active) * 100 if active else 0
            st.markdown(
                f'<div style="margin-bottom:12px">'
                f'<div style="display:flex;justify-content:space-between;margin-bottom:5px">'
                f'<span style="font-size:13px;color:{STAGE_COLOR[stage]};font-weight:600">{stage}</span>'
                f'<span style="font-size:12px;color:{C["muted"]}" class="num">{n} 家 · {fmt_money(arr)}</span>'
                f'</div>{progress_bar(share, STAGE_COLOR[stage])}</div>',
                unsafe_allow_html=True)
        st.caption("風險燈號由健康分數決定，與生命週期階段是兩個獨立維度 —— "
                   "成熟客戶一樣可能是紅燈。")

    st.write("")
    left, right = st.columns([3, 2])

    with left:
        st.markdown('<div class="sect">需要關注的客戶（紅燈與黃燈）</div>', unsafe_allow_html=True)
        watch = sorted([c for c in active if c["tier_color"] in ("red", "yellow")],
                       key=lambda c: c["health"])
        if not watch:
            st.success("目前沒有紅燈或黃燈客戶。")
        for c in watch:
            with st.container(border=True):
                a, b, d, e = st.columns([1, 4, 3, 1.4])
                a.markdown(health_ring(c["health"], TIER_COLOR[c["tier_color"]], 46),
                           unsafe_allow_html=True)
                b.markdown(
                    f'<div class="row-title">{c["name"]}</div>'
                    f'<div style="margin-top:4px">{pill(c["stage"], STAGE_COLOR[c["stage"]])}'
                    f'　{pill(c["tier"], TIER_COLOR[c["tier_color"]])}</div>'
                    f'<div class="row-sub" style="margin-top:5px">{c["csm"]}　·　'
                    f'{c["last_contact_days"]} 天前聯繫</div>', unsafe_allow_html=True)
                key, label = scoring.weakest_dimension(c["health_detail"])
                d.markdown(
                    f'<div class="row-sub">最弱構面</div>'
                    f'<div style="font-size:13px;color:{C["red"]};font-weight:600;margin:2px 0 6px">{label}</div>'
                    f'<div class="row-sub">{fmt_money(c["arr"])}　·　'
                    f'{c["days_to_renewal"]} 天後到期</div>', unsafe_allow_html=True)
                e.write("")
                if e.button("詳情", key=f"ov_{c['id']}", width="stretch"):
                    goto_detail(c["id"])

    with right:
        st.markdown('<div class="sect">本週必須處理</div>', unsafe_allow_html=True)
        top = [a for a in actions if a["urgent"]][:8]
        if not top:
            st.info("沒有逾期或緊急的待辦事項。")
        for i, a in enumerate(top):
            overdue = a["days"] is not None and a["days"] < 0
            color = C["red"] if overdue else C["yellow"]
            if overdue and abs(a["days"]) > 90:
                due_text = f"已延宕約 {abs(a['days']) // 30} 個月（原訂 {a['due']}）"
            elif overdue:
                due_text = f"已逾期 {abs(a['days'])} 天"
            elif a["days"]:
                due_text = f"{a['days']} 天後到期"
            else:
                due_text = "今日必須處理"
            st.markdown(
                f'<div class="panel" style="padding:11px 14px;margin-bottom:8px">'
                f'<div style="display:flex;justify-content:space-between;gap:8px">'
                f'<span style="font-size:12px;font-weight:600;color:{C["text"]}">{a["customer"]}</span>'
                f'{pill(a["type"], color)}</div>'
                f'<div style="font-size:12px;color:{C["muted"]};margin:6px 0 5px">{a["title"]}</div>'
                f'<div style="font-size:11px;color:{color}">{due_text}</div></div>',
                unsafe_allow_html=True)
        if len(actions) > len(top):
            st.caption(f"另有 {len(actions) - len(top)} 項非緊急待辦，見各客戶詳情頁。")


# ---------------------------------------------------------------- 頁面：客戶列表

def page_customers():
    st.markdown("### 客戶列表")

    f1, f2, f3 = st.columns([2, 2, 2])
    q = f1.text_input("搜尋客戶名稱", placeholder="輸入關鍵字…")
    stages = f2.multiselect("生命週期階段", STAGE_ORDER + ["已流失"], default=STAGE_ORDER)
    tiers = f3.multiselect("風險燈號", ["綠燈", "黃燈", "紅燈"],
                           default=["綠燈", "黃燈", "紅燈"])

    rows = [c for c in view
            if c["stage"] in stages and c["tier"] in tiers and (not q or q in c["name"])]
    rows.sort(key=lambda c: (not c["renewal_risk"], c["health"]))

    if not rows:
        st.info("沒有符合條件的客戶。")
        return

    df = pd.DataFrame([{
        "客戶名稱": c["name"],
        "階段": c["stage"],
        "健康分數": c["health"],
        "燈號": c["tier"],
        "ARR（萬）": (c["arr"] or 0) / 10000,
        # 本期新簽的客戶沒有「變動」可言，標示新簽比顯示 +全額 誠實
        # （Streamlit 的數值欄位會把空值渲染成 "None"，所以這些欄位改用文字）
        "ARR 變動": f"{c['arr_delta']/10000:+.1f} 萬" if c.get("prev_arr") else "本期新簽",
        "席位採用率": c["seat_rate"] or 0,
        "NPS": str(int(c["nps"])) if c.get("nps") is not None else "未回覆",
        "CSAT": f"{c['csat']:.1f}" if c.get("csat") is not None else "—",
        "到期天數": c["days_to_renewal"],
        "續約階段": (c.get("renewal") or {}).get("stage", "—"),
        "CSM": c["csm"],
        "續約風險": "⚠️" if c["renewal_risk"] else "",
    } for c in rows])

    st.caption(f"共 {len(rows)} 位客戶，續約風險者優先、其次依健康分數由低到高排序。"
               f"點選最左側的核取方塊即可進入該客戶的詳情頁。")
    event = st.dataframe(
        df, width="stretch", hide_index=True,
        on_select="rerun", selection_mode="single-row",
        key=f"cust_table_{st.session_state.table_nonce}",
        column_config={
            "健康分數": st.column_config.ProgressColumn(
                "健康分數", min_value=0, max_value=100, format="%.1f"),
            "ARR（萬）": st.column_config.NumberColumn("ARR（萬）", format="%.1f"),
            "ARR 變動": st.column_config.TextColumn("ARR 變動", help="與上期 ARR 相比"),
            "席位採用率": st.column_config.ProgressColumn(
                "席位採用率", min_value=0, max_value=100, format="%.0f%%"),
            "NPS": st.column_config.TextColumn("NPS", help="0-10 推薦分數"),
            "CSAT": st.column_config.TextColumn("CSAT", help="1-5 分滿意度平均"),
            "到期天數": st.column_config.NumberColumn("到期天數", format="%d 天"),
        },
    )

    picked = event.selection.rows
    if picked:
        goto_detail(rows[picked[0]]["id"])


# ---------------------------------------------------------------- 頁面：客戶詳情

def render_milestones(c):
    ms = c.get("milestones") or []
    if not ms:
        st.info("上傳模式沒有導入里程碑資料。切換到展示模式可看到完整範例。")
        return

    done = len([m for m in ms if m["status"] == "完成"])
    overdue = len([m for m in ms if m["status"] == "逾期"])
    a, b, d = st.columns(3)
    a.metric("里程碑完成", f"{done} / {len(ms)}")
    b.metric("逾期里程碑", overdue, delta=None if not overdue else "需處理", delta_color="inverse")
    d.metric("首次產生價值 TTV",
             f"{c['ttv_days']} 天" if c.get("ttv_days") else "尚未達成")

    st.write("")
    icon = {"完成": ("✓", C["green"]), "進行中": ("●", C["yellow"]),
            "逾期": ("!", C["red"]), "未開始": ("○", C["dim"])}
    for m in ms:
        mark, color = icon[m["status"]]
        delay = ""
        if m["delay_days"] is not None and m["delay_days"] > 3:
            delay = f'<span style="color:{C["yellow"]}">（延遲 {m["delay_days"] - 0} 天完成）</span>'
        st.markdown(
            f'<div class="mile">'
            f'<span style="color:{color};font-weight:700;width:16px">{mark}</span>'
            f'<div style="flex:1">'
            f'<div style="font-size:13px;color:{C["text"] if m["status"] != "未開始" else C["dim"]}">{m["name"]}</div>'
            f'<div class="row-sub">負責：{m["owner"]}　·　預計 {m["planned"]}'
            f'{"　·　實際 " + m["actual"] if m["actual"] else ""} {delay}</div></div>'
            f'{pill(m["status"], color)}</div>', unsafe_allow_html=True)


def render_meetings(c):
    ms = c.get("meetings") or []
    if not ms:
        st.info("上傳模式沒有會議紀錄資料。切換到展示模式可看到完整範例。")
        return

    qbrs = [m for m in ms if m["type"] in ("QBR", "EBR")]
    last_qbr = qbrs[0]["date"] if qbrs else "無紀錄"
    open_items = [cm for m in ms for cm in m["commitments"] if not cm["done"]]
    overdue = [cm for cm in open_items if cm.get("overdue")]

    a, b, d = st.columns(3)
    a.metric("最近一次 QBR／EBR", last_qbr)
    b.metric("未完成承諾事項", len(open_items))
    d.metric("其中已逾期", len(overdue),
             delta=None if not overdue else "需處理", delta_color="inverse")

    st.write("")
    for m in ms:
        with st.container(border=True):
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span class="row-title">{m["type"]}　<span class="row-sub">{m["date"]}</span></span>'
                f'{pill(m["type"], C["blue"] if m["type"] in ("QBR", "EBR") else C["indigo"])}</div>'
                f'<div class="row-sub" style="margin:6px 0">出席：{m["attendees"]}</div>'
                f'<div style="font-size:13px;color:{C["muted"]};margin-bottom:8px">{m["summary"]}</div>',
                unsafe_allow_html=True)
            for cm in m["commitments"]:
                if cm["done"]:
                    mark, color, note = "✓", C["green"], "已完成"
                elif cm.get("overdue"):
                    mark, color, note = "!", C["red"], f"逾期（原訂 {cm['due']}）"
                else:
                    mark, color, note = "○", C["yellow"], f"預計 {cm['due']}"
                st.markdown(
                    f'<div style="display:flex;gap:9px;padding:4px 0">'
                    f'<span style="color:{color};font-weight:700;width:14px">{mark}</span>'
                    f'<span style="flex:1;font-size:12px;color:{C["text"]}">{cm["item"]}'
                    f'<span class="row-sub">　（{cm["owner"]}）</span></span>'
                    f'<span style="font-size:11px;color:{color}">{note}</span></div>',
                    unsafe_allow_html=True)


def render_renewal(c):
    r = c.get("renewal") or {}
    if not r.get("stage"):
        st.info("上傳模式沒有續約進度資料。切換到展示模式可看到完整範例。")
        return

    a, b, d, e = st.columns(4)
    a.metric("距合約到期", f"{c['days_to_renewal']} 天", c["renewal_date"], delta_color="off")
    b.metric("續約金額", fmt_money(r.get("amount")))
    exp = r.get("expansion") or 0
    d.metric("擴展／縮減", f"{'+' if exp > 0 else ''}{fmt_money(exp)}" if exp else "持平",
             delta=f"{exp/  (c['prev_arr'] or 1) * 100:+.0f}%" if exp and c.get("prev_arr") else None)
    e.metric("預估成交機率", f"{r['probability']}%" if r.get("probability") is not None else "—")

    st.write("")
    st.markdown('<div class="sect">續約階段</div>', unsafe_allow_html=True)
    if r["stage"] == "已流失":
        st.error(f"已流失　·　原因：{c.get('churn_reason', '未紀錄')}")
    else:
        idx = RENEWAL_STAGES.index(r["stage"]) if r["stage"] in RENEWAL_STAGES else 0
        cols = st.columns(len(RENEWAL_STAGES))
        for i, (col, s) in enumerate(zip(cols, RENEWAL_STAGES)):
            if i < idx:
                mark, color = "✓", C["green"]
            elif i == idx:
                mark, color = "●", C["yellow"]
            else:
                mark, color = "○", C["dim"]
            col.markdown(
                f'<div style="text-align:center">'
                f'<div style="font-size:20px;color:{color}">{mark}</div>'
                f'<div style="font-size:11px;color:{color};font-weight:{700 if i == idx else 400}">{s}</div>'
                f'</div>', unsafe_allow_html=True)

    st.write("")
    if r.get("next_action"):
        overdue = r.get("next_action_in_days") is not None and r["next_action_in_days"] < 0
        color = C["red"] if (overdue or c["renewal_risk"]) else C["yellow"]
        st.markdown(
            f'<div class="panel" style="border-left:3px solid {color}">'
            f'<div class="row-sub">下一步行動　·　預計 {r.get("next_action_date") or "—"}</div>'
            f'<div style="font-size:14px;color:{C["text"]};margin-top:5px">{r["next_action"]}</div></div>',
            unsafe_allow_html=True)
    if r.get("note"):
        st.caption(f"備註：{r['note']}")


def render_contacts(c):
    cs = c.get("contacts") or []
    if not cs:
        st.info("上傳模式沒有聯絡人資料。切換到展示模式可看到完整範例。")
        return

    sentiment_color = {"支持": C["green"], "中立": C["yellow"], "反對": C["red"], "未知": C["dim"]}
    role_color = {"決策者": C["blue"], "Champion": C["green"],
                  "技術窗口": C["indigo"], "日常使用者": C["dim"]}

    has_champion = any(x["role"] == "Champion" and x["sentiment"] == "支持" for x in cs)
    if not has_champion:
        st.warning("此客戶目前沒有明確支持的 Champion —— 這是續約談判時最常被忽略的結構性風險。")

    for x in cs:
        with st.container(border=True):
            a, b = st.columns([3, 2])
            a.markdown(
                f'<div class="row-title">{x["name"]}　'
                f'<span class="row-sub">{x["title"]}</span></div>'
                f'<div style="margin-top:6px">{pill(x["role"], role_color.get(x["role"], C["dim"]))}'
                f'　{pill("態度：" + x["sentiment"], sentiment_color.get(x["sentiment"], C["dim"]))}</div>',
                unsafe_allow_html=True)
            last = x.get("last_contact_days")
            b.markdown(
                f'<div class="row-sub" style="text-align:right">最近互動</div>'
                f'<div style="text-align:right;font-size:14px;font-weight:600;'
                f'color:{C["red"] if last is None or last > 90 else C["text"]}">'
                f'{"從未接觸" if last is None else f"{last} 天前"}</div>',
                unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:12px;color:{C["muted"]};margin-top:6px">{x["note"]}</div>',
                        unsafe_allow_html=True)


def page_detail():
    ids = [c["id"] for c in view]
    if st.session_state.selected_id not in ids:
        st.session_state.selected_id = ids[0]

    top1, top2 = st.columns([5, 2])
    top1.markdown("### 客戶詳情")
    sel = top2.selectbox("切換客戶", ids, index=ids.index(st.session_state.selected_id),
                         format_func=lambda i: by_id[i]["name"], label_visibility="collapsed")
    if sel != st.session_state.selected_id:
        st.session_state.selected_id = sel
        st.rerun()

    c = by_id[sel]
    tcolor = TIER_COLOR[c["tier_color"]]

    with st.container(border=True):
        a, b, d = st.columns([1, 5, 3])
        a.markdown(health_ring(c["health"], tcolor, 84), unsafe_allow_html=True)
        b.markdown(
            f'<div style="font-size:21px;font-weight:800">{c["name"]}</div>'
            f'<div style="margin:8px 0">{pill(c["stage"], STAGE_COLOR[c["stage"]])}'
            f'　{pill(c["tier"] + "　" + TIER_TEXT[c["tier_color"]], tcolor)}'
            f'　{"　" + pill("續約風險", C["red"]) if c["renewal_risk"] else ""}</div>'
            f'<div style="font-size:13px;color:{C["muted"]}">'
            f'{c["industry"]}　·　{c["plan"]} 方案　·　負責 CSM：{c["csm"]}　·　'
            f'合約 {c.get("contract_start", "—")} 至 {c["renewal_date"]}</div>'
            f'<div style="margin-top:9px">'
            + "".join(f'<span class="tag">{t}</span>' for t in c.get("tags", []))
            + "</div>", unsafe_allow_html=True)
        delta = c["arr_delta"]
        d.markdown(
            f'<div style="text-align:right">'
            f'<div class="row-sub">年度經常性收入</div>'
            f'<div style="font-size:26px;font-weight:700" class="num">{fmt_money(c["arr"])}</div>'
            f'<div style="font-size:12px;color:'
            f'{C["green"] if delta > 0 else C["red"] if delta < 0 else C["dim"]}">'
            f'{"上期 " + fmt_money(c["prev_arr"]) + f"（{delta/c['prev_arr']*100:+.0f}%）" if c.get("prev_arr") else "本期新簽"}'
            f'</div></div>', unsafe_allow_html=True)

    st.write("")
    kpi_row([
        ("席位採用率", fmt_pct(c["seat_rate"], 0),
         f"{c.get('seats_active')} / {c.get('seats_purchased')} 席　閒置 {c['idle_seats']}",
         C["green"] if (c["seat_rate"] or 0) >= 70 else C["red"] if (c["seat_rate"] or 0) < 40 else C["yellow"]),
        ("近 30 天使用次數", fmt_num(c.get("usage_30d"), digits=0), "每月 20 次為滿分基準"),
        ("NPS 推薦分數", f"{c['nps']} / 10" if c.get("nps") is not None else "未回覆",
         "9-10 促進者　0-6 批評者",
         C["green"] if (c.get("nps") or 0) >= 9 else C["red"] if (c.get("nps") or 99) <= 6 else C["yellow"]),
        ("CSAT", f"{c['csat']} / 5" if c.get("csat") is not None else "—", "近 90 天平均",
         C["green"] if (c.get("csat") or 0) >= 4 else C["yellow"]),
        ("近 90 天工單", fmt_num(c.get("tickets_90d"), digits=0),
         f"其中緊急 {c.get('urgent_tickets_90d') or 0:.0f} 件"),
        ("距合約到期", f"{c['days_to_renewal']} 天", c["renewal_date"],
         C["red"] if c["days_to_renewal"] <= 30 else C["yellow"] if c["days_to_renewal"] <= 90 else None),
    ])

    st.write("")
    left, right = st.columns([2, 3])

    with left:
        st.markdown('<div class="sect">健康分數構面拆解</div>', unsafe_allow_html=True)
        detail = c["health_detail"]
        keys = list(detail.keys())
        fig = go.Figure(go.Bar(
            x=[detail[k]["score"] for k in keys],
            y=[f"{detail[k]['label']}　{detail[k]['weight']*100:.0f}%" for k in keys],
            orientation="h",
            marker=dict(color=[C["green"] if detail[k]["score"] >= 75
                               else C["yellow"] if detail[k]["score"] >= 50 else C["red"]
                               for k in keys]),
            text=[f"{detail[k]['score']:.0f}" for k in keys], textposition="auto",
        ))
        fig.update_xaxes(range=[0, 105])
        fig.update_yaxes(autorange="reversed")  # 權重高的構面排在最上面
        st.plotly_chart(dark_fig(fig, 260), width="stretch")
        st.caption("百分比是該構面在總分中的實際權重（缺資料的構面權重會分配給其他構面）。")

    with right:
        st.markdown('<div class="sect">風險說明與建議行動</div>', unsafe_allow_html=True)
        if use_ai and api_key:
            with st.spinner("Claude 生成中…"):
                try:
                    from anthropic import Anthropic
                    reason, action = advice.build_ai_advice(
                        Anthropic(api_key=api_key), "claude-haiku-4-5-20251001", c)
                    source = "Claude 生成"
                except Exception as e:
                    st.warning(f"AI 呼叫失敗，改用規則引擎（{e}）")
                    reason, action = advice.build_rule_based_advice(c)
                    source = "規則引擎"
        else:
            reason, action = advice.build_rule_based_advice(c)
            source = "規則引擎"

        st.markdown(
            f'<div class="panel" style="border-left:3px solid {tcolor}">'
            f'<div class="row-sub">風險說明　·　{source}</div>'
            f'<div style="font-size:13px;margin:6px 0 14px">{reason}</div>'
            f'<div class="row-sub">建議行動</div>'
            f'<div style="font-size:13px;margin-top:6px;color:{C["text"]}">{action}</div></div>',
            unsafe_allow_html=True)

    st.write("")
    t1, t2, t3, t4 = st.tabs(["導入進度里程碑", "QBR／會議紀錄", "續約進度", "聯絡人 / Champion 地圖"])
    with t1:
        render_milestones(c)
    with t2:
        render_meetings(c)
    with t3:
        render_renewal(c)
    with t4:
        render_contacts(c)


# ---------------------------------------------------------------- 頁面：續約管理

def page_renewals():
    st.markdown("### 續約管理")
    st.caption("業界標準做法是在合約到期前 90 天啟動續約流程，30 天內未進入議價即視為警訊。")

    pending = [c for c in active if c["days_to_renewal"] is not None and c["days_to_renewal"] >= 0]
    pending.sort(key=lambda c: c["days_to_renewal"])

    def window(days):
        return [c for c in pending if c["days_to_renewal"] <= days]

    w30, w60, w90 = window(30), window(60), window(90)
    weighted = sum((c["renewal"].get("amount") or 0) * (c["renewal"].get("probability") or 0) / 100
                   for c in w90)

    st.write("")
    kpi_row([
        ("30 天內到期", f"{len(w30)} 家", fmt_money(sum(c['arr'] for c in w30)), C["red"]),
        ("60 天內到期", f"{len(w60)} 家", fmt_money(sum(c['arr'] for c in w60)), C["yellow"]),
        ("90 天內到期", f"{len(w90)} 家", fmt_money(sum(c['arr'] for c in w90))),
        ("加權預估續約金額", fmt_money(weighted), "90 天內合約 × 成交機率", C["green"]),
        ("列為續約風險", f"{metrics['renewal_risk_count']} 家", "90 天內到期且黃／紅燈", C["red"]),
    ])

    st.write("")
    left, right = st.columns([2, 3])
    with left:
        st.markdown('<div class="sect">續約階段分佈（全部有效客戶）</div>', unsafe_allow_html=True)
        stage_counts = [(s, len([c for c in active if (c.get("renewal") or {}).get("stage") == s]))
                        for s in RENEWAL_STAGES]
        fig = go.Figure(go.Bar(
            x=[n for _, n in stage_counts], y=[s for s, _ in stage_counts], orientation="h",
            marker=dict(color=[C["dim"], C["indigo"], C["blue"], C["yellow"], C["green"]]),
            text=[str(n) for _, n in stage_counts], textposition="auto"))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(dark_fig(fig, 240), width="stretch")

    with right:
        st.markdown('<div class="sect">90 天內到期客戶：下一步行動</div>', unsafe_allow_html=True)
        if not w90:
            st.info("90 天內沒有到期合約。")
        for c in w90:
            r = c["renewal"]
            color = C["red"] if c["days_to_renewal"] <= 30 else C["yellow"]
            st.markdown(
                f'<div class="panel" style="border-left:3px solid {color};margin-bottom:9px">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span class="row-title">{c["name"]}</span>'
                f'<span class="num" style="font-size:13px;color:{color};font-weight:700">'
                f'{c["days_to_renewal"]} 天</span></div>'
                f'<div style="margin:6px 0">{pill(r.get("stage", "—"), color)}'
                f'　{pill(c["tier"], TIER_COLOR[c["tier_color"]])}'
                f'　<span class="row-sub">{fmt_money(r.get("amount"))}'
                f'　·　成交機率 {r.get("probability", "—")}%</span></div>'
                f'<div style="font-size:12px;color:{C["muted"]}">{r.get("next_action") or "—"}</div>'
                f'</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="sect">全部合約到期時程</div>', unsafe_allow_html=True)
    df = pd.DataFrame([{
        "客戶名稱": c["name"], "方案": c["plan"], "ARR（萬）": (c["arr"] or 0) / 10000,
        "到期日": c["renewal_date"], "剩餘天數": c["days_to_renewal"],
        "健康分數": c["health"], "燈號": c["tier"],
        "續約階段": (c.get("renewal") or {}).get("stage", "—"),
        "成交機率": (f"{(c.get('renewal') or {}).get('probability')}%"
                     if (c.get("renewal") or {}).get("probability") is not None else "—"),
        "CSM": c["csm"],
        "狀態": "緊急續約" if c["days_to_renewal"] <= 30 else
                "即將到期" if c["days_to_renewal"] <= 90 else "正常追蹤",
    } for c in pending])
    st.dataframe(df, width="stretch", hide_index=True, column_config={
        "ARR（萬）": st.column_config.NumberColumn("ARR（萬）", format="%.1f"),
        "剩餘天數": st.column_config.NumberColumn("剩餘天數", format="%d 天"),
        "健康分數": st.column_config.ProgressColumn("健康分數", min_value=0, max_value=100, format="%.1f"),
        "成交機率": st.column_config.TextColumn("成交機率"),
    })


# ---------------------------------------------------------------- 頁面：指標字典

def page_glossary():
    st.markdown("### 指標字典")
    st.caption("這一頁說明每個指標的定義、公式與本儀表板的實際數值 —— "
               "指標定義不一致是 CSM 團隊最常見的溝通成本來源。")

    def table(header, rows):
        lines = ["| " + " | ".join(header) + " |",
                 "|" + "|".join([":--"] * len(header)) + "|"]
        lines += ["| " + " | ".join(r) + " |" for r in rows]
        st.markdown(md_safe("\n".join(lines)), unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="sect">收入類指標</div>', unsafe_allow_html=True)
    table(["指標", "公式", "本表數值", "為什麼重要"], [
        ["**ARR**<br>年度經常性收入", "所有有效客戶的年約金額加總", fmt_money(metrics["arr"]),
         "CSM 管理的資產總量，所有留存指標的分母基礎。"],
        ["**NRR**<br>淨收入留存率", "(期初 ARR ＋擴展 −縮減 −流失) ÷ 期初 ARR", fmt_pct(metrics["nrr"]),
         "SaaS 最重要的單一指標。超過 100% 代表既有客戶自己就能帶來成長，"
         "優秀的 B2B SaaS 通常落在 110–120%。"],
        ["**GRR**<br>總收入留存率", "(期初 ARR −縮減 −流失) ÷ 期初 ARR，不計擴展", fmt_pct(metrics["grr"]),
         "上限 100%。NRR 可能被少數大客戶的擴展掩蓋掉流失，"
         "GRR 才看得出真實的留存體質。兩個一起看才完整。"],
        ["**客戶留存率**<br>Logo Retention", "期末仍有效的客戶數 ÷ 期初客戶數",
         fmt_pct(metrics["logo_retention"]),
         "看「家數」而不是金額。小客戶流失多但金額小的時候，"
         "NRR 會很好看、Logo 留存卻很差。"],
    ])

    if metrics["start_arr"]:
        st.info(md_safe(
            f"NRR 的分母是上期就存在的 "
            f"{len([c for c in view if (c.get('prev_arr') or 0) > 0])} 家客戶"
            f"（{fmt_money(metrics['start_arr'])}），本期新簽的客戶不列入 —— 這是 NRR 最常被算錯的地方。"
            f"　期末 {fmt_money(metrics['end_arr'])} ＝ 期初 {fmt_money(metrics['start_arr'])}"
            f" ＋擴展 {fmt_money(metrics['expansion'])}"
            f" －縮減 {fmt_money(metrics['contraction'])}"
            f" －流失 {fmt_money(metrics['churn_arr'])}。"))
    else:
        st.info("目前的資料沒有「上期ARR」欄位，NRR 與 GRR 無法計算。"
                "留存率必須有兩個時間點才算得出來。")

    st.write("")
    st.markdown('<div class="sect">體驗與採用類指標</div>', unsafe_allow_html=True)
    table(["指標", "公式", "本表數值", "為什麼重要"], [
        ["**NPS**<br>淨推薦值", "促進者(9–10 分)% − 批評者(0–6 分)%，7–8 分為被動者不計",
         fmt_nps(metrics["nps"]),
         "測「忠誠度與推薦意願」，範圍 −100 到 +100。B2B SaaS 30 以上算好。"],
        ["**CSAT**<br>顧客滿意度", "單次互動後的 1–5 分評價取平均",
         f"{metrics['csat']} / 5" if metrics["csat"] else "—",
         "測「單次體驗」，跟 NPS 是兩個不同的東西。CSAT 高但 NPS 低＝"
         "服務態度好，但產品沒解決客戶的核心問題。"],
        ["**席位採用率**", "活躍席位 ÷ 已購席位",
         f"{fmt_pct(metrics['seat_rate'])}（閒置 {metrics['idle_seats']:,} 席）",
         "續約談判時客戶最常用的砍價理由。低採用率＝下一期幾乎一定被要求降額。"],
        ["**TTV**<br>Time to Value", "從簽約到客戶首次獲得實際價值的天數",
         f"平均 {metrics['avg_ttv']} 天" if metrics["avg_ttv"] else "—",
         "第一年流失最強的預測指標。TTV 越長，客戶越可能在還沒感受到價值前就決定不續約。"],
    ])

    st.write("")
    st.markdown('<div class="sect">健康分數計算方式</div>', unsafe_allow_html=True)
    table(["構面", "權重", "計算方式"], [
        ["席位採用率", "25%", "活躍席位 ÷ 已購席位 × 100"],
        ["使用頻率", "15%", "近 30 天使用次數 ÷ 20 × 100（上限 100）"],
        ["客服健康度", "20%", "100 − 工單數×5 − 緊急工單數×15"],
        ["導入完成度", "15%", "導入完成百分比直接採用"],
        ["滿意度", "15%", "NPS(0–10)×10 與 CSAT 換算成百分制後取平均"],
        ["互動新鮮度", "10%", "100 − 距最近互動天數×1.2"],
    ])
    st.caption("某個構面沒有資料時（例如客戶還沒回覆 NPS），該構面的權重會按比例分配給其他構面，"
               "而不是以 0 分計算 —— 缺資料不等於表現差。")

    a, b = st.columns(2)
    a.markdown(
        f'<div class="panel"><div class="sect">燈號門檻</div>'
        f'<div style="font-size:13px;line-height:2">'
        f'{pill("綠燈", C["green"])}　75 分以上　·　依既定節奏經營，找擴展機會<br>'
        f'{pill("黃燈", C["yellow"])}　50 – 74 分　·　需主動介入，找出並修正最弱構面<br>'
        f'{pill("紅燈", C["red"])}　50 分以下　·　啟動健康度復原計畫，必要時高層介入'
        f'</div></div>', unsafe_allow_html=True)
    b.markdown(
        f'<div class="panel"><div class="sect">兩個獨立維度</div>'
        f'<div style="font-size:13px;color:{C["muted"]};line-height:1.9">'
        f'<b style="color:{C["text"]}">生命週期階段</b>（導入 → 採用 → 成熟 → 續約中）'
        f'描述客戶「走到哪裡」，決定 CSM 該做什麼類型的工作。<br><br>'
        f'<b style="color:{C["text"]}">風險燈號</b>由健康分數決定，描述客戶「狀況好不好」。<br><br>'
        f'兩者互不隸屬 —— 成熟客戶可能是紅燈，導入客戶也可能一路綠燈。'
        f'把「流失風險」當成生命週期的一個階段是常見的設計錯誤。'
        f'</div></div>', unsafe_allow_html=True)

    st.write("")
    st.caption("資料來源說明：展示模式的所有客戶、人名、金額與事件皆為虛構，"
               "用於呈現工具能力，不對應任何真實企業或個人。")


# ---------------------------------------------------------------- 路由

PAGE_FUNCS = {
    "總覽": page_overview,
    "客戶列表": page_customers,
    "客戶詳情": page_detail,
    "續約管理": page_renewals,
    "指標字典": page_glossary,
}
PAGE_FUNCS[st.session_state.nav]()
