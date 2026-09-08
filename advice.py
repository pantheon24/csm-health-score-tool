"""風險說明與建議行動的生成：預設用規則引擎，有 API 金鑰時可切換成 Claude。"""

import os

import scoring

DIMENSION_DIAGNOSIS = {
    "seat_adoption": "已購席位大量閒置",
    "usage": "使用頻率偏低",
    "support": "客服工單量偏高",
    "onboarding": "導入完成度不足",
    "satisfaction": "客戶滿意度偏低",
    "freshness": "太久沒有互動",
}


def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        import streamlit as st

        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        return None


def build_rule_based_advice(c):
    """依最弱構面產生風險說明與建議行動。不需要任何 API。"""
    key, label = scoring.weakest_dimension(c.get("health_detail") or {})
    name = c["name"]
    reason = f"{name} 目前健康分數 {c['health']} 分（{c['tier']}），最弱的構面是「{label}」"

    if key == "seat_adoption":
        reason += f"：已購 {c.get('seats_purchased')} 席中只有 {c.get('seats_active')} 席活躍，閒置 {c.get('idle_seats')} 席。"
        action = "先做一次部門別使用率拆解，找出完全沒登入的單位，針對該單位設計情境式教育訓練；閒置席位是續約談判時最容易被拿來砍價的破口，要在進入續約窗口前處理掉。"
    elif key == "usage":
        reason += f"：近 30 天僅使用 {c.get('usage_30d')} 次。"
        action = "安排一次使用狀況確認通話，釐清是卡在功能不會用、流程不合、還是需求已改變；三種原因對應的解法完全不同，不要先跳到教育訓練。"
    elif key == "support":
        reason += f"：近 90 天有 {c.get('tickets_90d')} 件工單，其中 {c.get('urgent_tickets_90d')} 件緊急。"
        action = "逐一盤點未收斂的工單，把重複發生的問題升級為跨部門處理並給出明確時程表；工單累積會直接侵蝕決策者對產品的信任。"
    elif key == "onboarding":
        reason += f"：導入完成度僅 {c.get('onboarding_pct')}%。"
        action = "重擬導入計畫，把剩餘里程碑重新排期並指定客戶端負責人；導入卡關是第一年流失最主要的單一原因，優先度高於其他所有工作。"
    elif key == "satisfaction":
        detail = []
        if c.get("nps") is not None:
            detail.append(f"NPS 推薦分數 {c['nps']}/10")
        if c.get("csat") is not None:
            detail.append(f"CSAT {c['csat']}/5")
        reason += "：" + "、".join(detail) + "。"
        action = "安排一次不談產品的訪談，問清楚「當初買這套是想解決什麼、現在解決了幾成」，把落差寫成書面改善計畫並約定回檢日期。"
    else:
        reason += f"：距今 {c.get('last_contact_days')} 天沒有任何互動紀錄。"
        action = "本週內先取得一通電話重建聯繫節奏，並確認原本的窗口是否仍在職；長期斷聯通常代表 Champion 已流失，而不只是忙。"

    # 疊加情境式提醒
    extra = []
    if c.get("renewal_risk"):
        extra.append(f"合約將在 {c['days_to_renewal']} 天內到期且燈號為{c['tier']}，應列為本週最優先處理對象。")

    champions = [x for x in c.get("contacts", []) if x.get("role") == "Champion"]
    if not champions and c.get("contacts"):
        extra.append("目前沒有明確的 Champion，建議在客戶端培養一位有影響力的內部推手。")

    decision_makers = [x for x in c.get("contacts", []) if x.get("role") == "決策者"]
    for dm in decision_makers:
        d = dm.get("last_contact_days")
        if d is None:
            extra.append(f"從未接觸過決策者（{dm['title']}），續約缺乏支點，需儘快建立關係。")
        elif d > 90:
            extra.append(f"決策者 {dm['name']}（{dm['title']}）已 {d} 天未互動，續約前必須重新接觸。")

    if extra:
        action += " " + " ".join(extra)

    return reason, action


CLAUDE_PROMPT = """你是一位資深的客戶成功經理（CSM）主管。請針對以下客戶，用繁體中文寫出「風險說明」與「建議行動」，各 2-3 句話。要求：具體、可執行、指出根因而非表面現象，不要寫空泛的場面話。

客戶名稱：{name}
產業：{industry}｜方案：{plan}｜生命週期階段：{stage}
健康分數：{health} / 100（{tier}）
各構面分數：{dims}
ARR：{arr:,}（上期 {prev_arr:,}）
席位：已購 {seats_purchased} / 活躍 {seats_active}
近 30 天使用次數：{usage_30d}
近 90 天工單：{tickets_90d} 件（緊急 {urgent_tickets_90d} 件）
導入完成度：{onboarding_pct}%
NPS 推薦分數：{nps}／CSAT：{csat}
距最近互動：{last_contact_days} 天
距合約到期：{days_to_renewal} 天｜續約階段：{renewal_stage}
關鍵聯絡人：{contacts}

請用以下格式輸出，不要加其他文字：
風險說明：...
建議行動：..."""


def build_ai_advice(client, model, c):
    dims = "、".join(
        f"{v['label']} {v['score']}" for v in (c.get("health_detail") or {}).values()
    )
    contacts = "；".join(
        f"{x['name']}（{x['title']}／{x['role']}／態度{x['sentiment']}）"
        for x in c.get("contacts", [])
    ) or "無紀錄"

    prompt = CLAUDE_PROMPT.format(
        name=c["name"],
        industry=c.get("industry", "-"),
        plan=c.get("plan", "-"),
        stage=c.get("stage", "-"),
        health=c["health"],
        tier=c["tier"],
        dims=dims,
        arr=c.get("arr") or 0,
        prev_arr=c.get("prev_arr") or 0,
        seats_purchased=c.get("seats_purchased", "-"),
        seats_active=c.get("seats_active", "-"),
        usage_30d=c.get("usage_30d", "-"),
        tickets_90d=c.get("tickets_90d", "-"),
        urgent_tickets_90d=c.get("urgent_tickets_90d", "-"),
        onboarding_pct=c.get("onboarding_pct", "-"),
        nps=c.get("nps", "未提供"),
        csat=c.get("csat", "未提供"),
        last_contact_days=c.get("last_contact_days", "-"),
        days_to_renewal=c.get("days_to_renewal", "-"),
        renewal_stage=(c.get("renewal") or {}).get("stage", "-"),
        contacts=contacts,
    )

    message = client.messages.create(
        model=model, max_tokens=600, messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text

    reason, action, current = "", "", None
    for line in text.splitlines():
        if line.startswith("風險說明："):
            current = "reason"
            reason = line.replace("風險說明：", "").strip()
        elif line.startswith("建議行動："):
            current = "action"
            action = line.replace("建議行動：", "").strip()
        elif line.strip() and current == "reason":
            reason += line.strip()
        elif line.strip() and current == "action":
            action += line.strip()

    return reason or text, action
