import os
from datetime import date

import pandas as pd
import streamlit as st

REQUIRED_COLUMNS = [
    "客戶名稱", "合約金額", "合約到期日", "近30天使用次數",
    "近90天客服工單數", "近90天緊急工單數", "導入完成度(%)",
    "滿意度分數(NPS/CSAT)", "距今最近互動天數",
]

WEIGHTS = {"usage": 0.30, "support": 0.25, "onboarding": 0.15, "satisfaction": 0.15, "freshness": 0.15}
RENEWAL_WINDOW_DAYS = 90

st.set_page_config(page_title="客戶健康分數＋續約風險預警", layout="wide")


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def compute_scores(row):
    usage_score = clamp(row["近30天使用次數"] / 20 * 100)
    support_score = clamp(100 - row["近90天客服工單數"] * 5 - row["近90天緊急工單數"] * 15)
    onboarding_score = clamp(row["導入完成度(%)"])
    freshness_score = clamp(100 - row["距今最近互動天數"] * 1.2)

    parts = {"usage": usage_score, "support": support_score,
             "onboarding": onboarding_score, "freshness": freshness_score}

    nps = row["滿意度分數(NPS/CSAT)"]
    if pd.notna(nps):
        parts["satisfaction"] = clamp(nps / 10 * 100)

    total_weight = sum(WEIGHTS[k] for k in parts)
    weighted_sum = sum(WEIGHTS[k] * parts[k] for k in parts)
    final_score = weighted_sum / total_weight if total_weight else 0

    return round(final_score, 1), {k: round(v, 1) for k, v in parts.items()}


def risk_tier(score):
    if score >= 75:
        return "🟢 綠燈", "green"
    if score >= 50:
        return "🟡 黃燈", "orange"
    return "🔴 紅燈", "red"


def process_dataframe(df):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV 缺少必要欄位：{', '.join(missing)}")

    today = date.today()
    results = []
    for _, row in df.iterrows():
        score, sub_scores = compute_scores(row)
        tier_label, tier_color = risk_tier(score)

        renewal_date = pd.to_datetime(row["合約到期日"]).date()
        days_to_renewal = (renewal_date - today).days
        renewal_risk = days_to_renewal <= RENEWAL_WINDOW_DAYS and tier_color in ("orange", "red")

        results.append({
            "客戶名稱": row["客戶名稱"],
            "健康分數": score,
            "風險燈號": tier_label,
            "tier_color": tier_color,
            "續約風險": renewal_risk,
            "合約到期日": renewal_date,
            "距到期天數": days_to_renewal,
            "合約金額": row["合約金額"],
            "sub_scores": sub_scores,
            "raw": row,
        })

    out = pd.DataFrame(results)
    out = out.sort_values(by=["續約風險", "健康分數"], ascending=[False, True]).reset_index(drop=True)
    return out


def weakest_dimension(sub_scores):
    label_map = {
        "usage": "使用頻率偏低",
        "support": "客服工單偏多",
        "onboarding": "導入/教育訓練完成度不足",
        "satisfaction": "滿意度偏低",
        "freshness": "太久沒有互動",
    }
    weakest_key = min(sub_scores, key=sub_scores.get)
    return label_map[weakest_key], weakest_key


def build_rule_based_advice(name, row, sub_scores):
    weakest_label, weakest_key = weakest_dimension(sub_scores)
    raw = row["raw"]

    reason = f"{name} 目前健康分數為 {row['健康分數']} 分，主要原因是「{weakest_label}」"
    if weakest_key == "usage":
        reason += f"（近30天僅使用 {int(raw['近30天使用次數'])} 次）。"
        action = "建議安排一次產品使用狀況確認電話，了解是否卡在某個功能，並提供對應教學或簡化流程。"
    elif weakest_key == "support":
        reason += f"（近90天有 {int(raw['近90天客服工單數'])} 件客服工單，其中 {int(raw['近90天緊急工單數'])} 件為緊急）。"
        action = "建議主動聯繫，逐一檢視未解決的問題是否已妥善收斂，必要時安排跨部門會議處理根本原因。"
    elif weakest_key == "onboarding":
        reason += f"（導入完成度僅 {int(raw['導入完成度(%)'])}%）。"
        action = "建議重啟導入計畫，安排一場聚焦剩餘步驟的教育訓練，加速客戶上手。"
    elif weakest_key == "satisfaction":
        reason += f"（滿意度分數為 {raw['滿意度分數(NPS/CSAT)']}）。"
        action = "建議安排訪談了解不滿意的具體原因，並與客戶共同訂出改善計畫。"
    else:
        reason += f"（距今 {int(raw['距今最近互動天數'])} 天沒有互動紀錄）。"
        action = "建議立即安排一次關懷聯繫，重新建立聯繫節奏，避免關係持續冷卻。"

    if row["續約風險"]:
        action += f" 由於合約將在 {int(row['距到期天數'])} 天內到期，建議列為本週優先處理對象。"

    return reason, action


def build_ai_advice(client, model, name, row, sub_scores):
    raw = row["raw"]
    prompt = f"""你是一位資深的客戶成功經理（CSM）助理。請針對以下客戶，用繁體中文寫出「風險說明」與「建議行動」，各 1-2 句話，語氣專業、具體、可執行，不要空泛的建議。

客戶名稱：{name}
健康分數：{row['健康分數']} / 100
近30天使用次數：{int(raw['近30天使用次數'])}
近90天客服工單數：{int(raw['近90天客服工單數'])}（其中緊急 {int(raw['近90天緊急工單數'])} 件）
導入/教育訓練完成度：{int(raw['導入完成度(%)'])}%
滿意度分數：{raw['滿意度分數(NPS/CSAT)'] if pd.notna(raw['滿意度分數(NPS/CSAT)']) else '未提供'}
距今最近互動天數：{int(raw['距今最近互動天數'])} 天
距合約到期天數：{int(row['距到期天數'])} 天
是否列為續約風險：{'是' if row['續約風險'] else '否'}

請用以下格式輸出，不要加其他文字：
風險說明：...
建議行動：..."""

    message = client.messages.create(
        model=model,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text
    reason, action = "", ""
    for line in text.splitlines():
        if line.startswith("風險說明："):
            reason = line.replace("風險說明：", "").strip()
        elif line.startswith("建議行動："):
            action = line.replace("建議行動：", "").strip()
    return reason or text, action


st.title("客戶健康分數＋續約風險預警")
st.caption("上傳客戶資料 CSV，自動算出健康分數、風險燈號，並產生風險說明與建議行動。")

with st.expander("需要 CSV 範本嗎？點這裡看欄位格式"):
    st.code(",".join(REQUIRED_COLUMNS), language=None)
    st.write("「滿意度分數(NPS/CSAT)」可以留空，其餘欄位為必填。")

def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        return None


api_key = get_api_key()
use_real_ai = st.toggle(
    "使用真實 AI（Claude API）生成風險說明",
    value=bool(api_key),
    disabled=not api_key,
    help="需要設定 ANTHROPIC_API_KEY 才能開啟；未設定時會使用規則引擎生成的說明。",
)
if not api_key:
    st.caption("⚠️ 尚未偵測到 ANTHROPIC_API_KEY，目前使用規則引擎生成風險說明（見 README 設定金鑰）。")

uploaded = st.file_uploader("上傳客戶資料 CSV", type=["csv"])

if uploaded:
    try:
        df = pd.read_csv(uploaded)
        result = process_dataframe(df)
    except Exception as e:
        st.error(f"讀取 CSV 發生問題：{e}")
        st.stop()

    tiers = st.multiselect("篩選風險燈號", ["🟢 綠燈", "🟡 黃燈", "🔴 紅燈"],
                            default=["🟢 綠燈", "🟡 黃燈", "🔴 紅燈"])
    filtered = result[result["風險燈號"].isin(tiers)]

    st.subheader(f"客戶清單（共 {len(filtered)} 位，依風險排序）")

    client = None
    if use_real_ai and api_key:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

    for _, row in filtered.iterrows():
        badge_color = {"green": "#1a7f37", "orange": "#b35c00", "red": "#c0342c"}[row["tier_color"]]
        header = f"{row['風險燈號']}　**{row['客戶名稱']}**　健康分數 {row['健康分數']}"
        if row["續約風險"]:
            header += "　🔺續約風險"

        with st.container(border=True):
            st.markdown(
                f"<span style='color:{badge_color};font-weight:600'>{header}</span>",
                unsafe_allow_html=True,
            )
            cols = st.columns(4)
            cols[0].metric("合約到期日", str(row["合約到期日"]))
            cols[1].metric("距到期天數", int(row["距到期天數"]))
            cols[2].metric("合約金額", f"{int(row['合約金額']):,}")
            cols[3].metric("風險燈號", row["風險燈號"])

            if row["tier_color"] in ("orange", "red"):
                if client:
                    with st.spinner("AI 生成風險說明中..."):
                        try:
                            reason, action = build_ai_advice(
                                client, "claude-haiku-4-5-20251001",
                                row["客戶名稱"], row, row["sub_scores"],
                            )
                        except Exception as e:
                            st.warning(f"AI 呼叫失敗，改用規則引擎生成（{e}）")
                            reason, action = build_rule_based_advice(row["客戶名稱"], row, row["sub_scores"])
                else:
                    reason, action = build_rule_based_advice(row["客戶名稱"], row, row["sub_scores"])

                st.markdown(f"**風險說明**：{reason}")
                st.markdown(f"**建議行動**：{action}")
else:
    st.info("請上傳 CSV 開始分析，或先展開上方範本查看欄位格式。")
