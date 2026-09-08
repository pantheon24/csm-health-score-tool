"""健康分數與 CSM 組合層指標的計算邏輯。

拆成獨立模組的原因：計分規則是這個工具的核心資產，
要能被單獨檢視、單獨修改、單獨驗證，不該埋在畫面程式碼裡。
"""

from datetime import date

# ---------------------------------------------------------------- 健康分數

# 六個構面與權重（總和 100%）。某個構面缺資料時，權重會依比例重新分配給其餘構面。
DIMENSIONS = {
    "seat_adoption": {"label": "席位採用率", "weight": 0.25},
    "usage": {"label": "使用頻率", "weight": 0.15},
    "support": {"label": "客服健康度", "weight": 0.20},
    "onboarding": {"label": "導入完成度", "weight": 0.15},
    "satisfaction": {"label": "滿意度", "weight": 0.15},
    "freshness": {"label": "互動新鮮度", "weight": 0.10},
}

GREEN_THRESHOLD = 75
YELLOW_THRESHOLD = 50
RENEWAL_WINDOW_DAYS = 90


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def _seat_adoption(c):
    purchased = c.get("seats_purchased")
    active = c.get("seats_active")
    if not purchased:
        return None
    return clamp(active / purchased * 100)


def _usage(c):
    v = c.get("usage_30d")
    if v is None:
        return None
    # 每月 20 次（約每個工作日一次）視為滿分
    return clamp(v / 20 * 100)


def _support(c):
    tickets = c.get("tickets_90d")
    if tickets is None:
        return None
    urgent = c.get("urgent_tickets_90d") or 0
    return clamp(100 - tickets * 5 - urgent * 15)


def _onboarding(c):
    v = c.get("onboarding_pct")
    return None if v is None else clamp(v)


def _satisfaction(c):
    """NPS 推薦分數（0-10）與 CSAT（1-5）各自換算成 0-100 後取平均。"""
    parts = []
    nps = c.get("nps")
    if nps is not None:
        parts.append(clamp(nps / 10 * 100))
    csat = c.get("csat")
    if csat is not None:
        parts.append(clamp((csat - 1) / 4 * 100))
    if not parts:
        return None
    return sum(parts) / len(parts)


def _freshness(c):
    v = c.get("last_contact_days")
    if v is None:
        return None
    # 每過一天扣 1.2 分，約 83 天沒互動就歸零
    return clamp(100 - v * 1.2)


_CALCULATORS = {
    "seat_adoption": _seat_adoption,
    "usage": _usage,
    "support": _support,
    "onboarding": _onboarding,
    "satisfaction": _satisfaction,
    "freshness": _freshness,
}


def compute_health(customer):
    """回傳 (總分, 各構面明細)。缺資料的構面會被排除並重新分配權重。"""
    parts = {}
    for key, fn in _CALCULATORS.items():
        score = fn(customer)
        if score is not None:
            parts[key] = score

    total_weight = sum(DIMENSIONS[k]["weight"] for k in parts)
    if not total_weight:
        return 0.0, {}

    final = sum(DIMENSIONS[k]["weight"] * v for k, v in parts.items()) / total_weight

    detail = {
        k: {
            "label": DIMENSIONS[k]["label"],
            "score": round(v, 1),
            "weight": round(DIMENSIONS[k]["weight"] / total_weight, 3),
        }
        for k, v in parts.items()
    }
    return round(final, 1), detail


def risk_tier(score):
    if score >= GREEN_THRESHOLD:
        return "綠燈", "green"
    if score >= YELLOW_THRESHOLD:
        return "黃燈", "yellow"
    return "紅燈", "red"


def weakest_dimension(detail):
    if not detail:
        return None, None
    key = min(detail, key=lambda k: detail[k]["score"])
    return key, detail[key]["label"]


def enrich(customers, today=None):
    """為每位客戶補上健康分數、燈號、續約風險等衍生欄位。"""
    today = today or date.today()
    out = []
    for c in customers:
        c = dict(c)
        score, detail = compute_health(c)
        tier_label, tier_color = risk_tier(score)

        c["health"] = score
        c["health_detail"] = detail
        c["tier"] = tier_label
        c["tier_color"] = tier_color

        days = c.get("renewal_in_days")
        if days is None and c.get("renewal_date"):
            days = (date.fromisoformat(c["renewal_date"]) - today).days
        c["days_to_renewal"] = days

        c["renewal_risk"] = bool(
            c.get("status") == "active"
            and days is not None
            and 0 <= days <= RENEWAL_WINDOW_DAYS
            and tier_color in ("yellow", "red")
        )

        purchased = c.get("seats_purchased") or 0
        active = c.get("seats_active") or 0
        c["idle_seats"] = max(purchased - active, 0)
        c["seat_rate"] = round(active / purchased * 100, 1) if purchased else None

        c["arr_delta"] = (c.get("arr") or 0) - (c.get("prev_arr") or 0)
        out.append(c)
    return out


# ---------------------------------------------------------------- 組合層指標


def portfolio_metrics(customers):
    """算出整個客戶組合的管理指標。customers 需已經過 enrich()。"""
    active = [c for c in customers if c.get("status") == "active"]
    churned = [c for c in customers if c.get("status") == "churned"]

    # NRR / GRR 的分母是「期初就存在的客戶」（cohort），本期新簽客戶不列入
    cohort = [c for c in customers if (c.get("prev_arr") or 0) > 0]
    start_arr = sum(c["prev_arr"] for c in cohort)
    end_arr = sum(c.get("arr") or 0 for c in cohort)
    retained_arr = sum(min(c.get("arr") or 0, c["prev_arr"]) for c in cohort)

    expansion = sum(max((c.get("arr") or 0) - c["prev_arr"], 0) for c in cohort)
    contraction = sum(
        max(c["prev_arr"] - (c.get("arr") or 0), 0)
        for c in cohort
        if c.get("status") == "active"
    )
    churn_arr = sum(c["prev_arr"] for c in cohort if c.get("status") == "churned")

    nrr = end_arr / start_arr * 100 if start_arr else None
    grr = retained_arr / start_arr * 100 if start_arr else None

    cohort_churned = [c for c in cohort if c.get("status") == "churned"]
    logo_retention = (
        (len(cohort) - len(cohort_churned)) / len(cohort) * 100 if cohort else None
    )

    # NPS 依標準定義計算：促進者(9-10)% − 批評者(0-6)%
    nps_scores = [c["nps"] for c in active if c.get("nps") is not None]
    if nps_scores:
        promoters = len([s for s in nps_scores if s >= 9])
        detractors = len([s for s in nps_scores if s <= 6])
        nps = round((promoters - detractors) / len(nps_scores) * 100)
    else:
        promoters = detractors = 0
        nps = None

    csat_scores = [c["csat"] for c in active if c.get("csat") is not None]
    ttvs = [c["ttv_days"] for c in customers if c.get("ttv_days") is not None]

    seats_purchased = sum(c.get("seats_purchased") or 0 for c in active)
    seats_active = sum(c.get("seats_active") or 0 for c in active)

    renewing = [
        c for c in active
        if c.get("days_to_renewal") is not None and 0 <= c["days_to_renewal"] <= RENEWAL_WINDOW_DAYS
    ]

    return {
        "arr": sum(c.get("arr") or 0 for c in active),
        "customer_count": len(active),
        "nrr": nrr,
        "grr": grr,
        "start_arr": start_arr,
        "end_arr": end_arr,
        "expansion": expansion,
        "contraction": contraction,
        "churn_arr": churn_arr,
        "logo_retention": logo_retention,
        "churned_count": len(churned),
        "avg_health": round(sum(c["health"] for c in active) / len(active), 1) if active else None,
        "at_risk": len([c for c in active if c["tier_color"] == "red"]),
        "watch": len([c for c in active if c["tier_color"] == "yellow"]),
        "nps": nps,
        "nps_promoters": promoters,
        "nps_detractors": detractors,
        "nps_respondents": len(nps_scores),
        "csat": round(sum(csat_scores) / len(csat_scores), 2) if csat_scores else None,
        "seat_rate": round(seats_active / seats_purchased * 100, 1) if seats_purchased else None,
        "idle_seats": seats_purchased - seats_active,
        "avg_ttv": round(sum(ttvs) / len(ttvs)) if ttvs else None,
        "renewing_count": len(renewing),
        "renewing_arr": sum(c.get("arr") or 0 for c in renewing),
        "renewal_risk_count": len([c for c in active if c.get("renewal_risk")]),
    }


# ---------------------------------------------------------------- 行動清單


TYPE_RANK = {"續約": 0, "會議承諾": 1, "導入里程碑": 2, "客戶待辦": 3}


def build_action_items(customers, today=None):
    """從三個來源自動彙整出 CSM 的待辦：續約下一步、逾期承諾、逾期導入里程碑。

    同一位客戶的多個逾期里程碑會收斂成一筆，避免待辦清單被同一件事洗版。
    """
    today = today or date.today()
    items = []

    for c in customers:
        if c.get("status") != "active":
            continue

        r = c.get("renewal") or {}
        if r.get("next_action") and r.get("next_action_in_days") is not None:
            days = r["next_action_in_days"]
            items.append({
                "customer": c["name"],
                "customer_id": c["id"],
                "type": "續約",
                "title": r["next_action"],
                "due": r.get("next_action_date"),
                "days": days,
                "urgent": days <= 3 or bool(c.get("renewal_risk")),
            })

        for m in c.get("meetings", []):
            for cm in m.get("commitments", []):
                if cm.get("done"):
                    continue
                items.append({
                    "customer": c["name"],
                    "customer_id": c["id"],
                    "type": "會議承諾" if cm.get("owner") == "CSM" else "客戶待辦",
                    "title": cm["item"],
                    "due": cm.get("due"),
                    "days": cm.get("due_in_days"),
                    "urgent": bool(cm.get("overdue")),
                })

        overdue_ms = [m for m in c.get("milestones", []) if m.get("status") == "逾期"]
        if overdue_ms:
            first = overdue_ms[0]
            n = len(overdue_ms)
            suffix = f"（共 {n} 個里程碑逾期）" if n > 1 else ""
            items.append({
                "customer": c["name"],
                "customer_id": c["id"],
                "type": "導入里程碑",
                "title": f"導入未結案，卡在「{first['name']}」{suffix}",
                "due": first.get("planned"),
                "days": (date.fromisoformat(first["planned"]) - today).days,
                "urgent": True,
            })

    items.sort(key=lambda x: (
        not x["urgent"],
        TYPE_RANK.get(x["type"], 9),
        x["days"] if x["days"] is not None else 999,
    ))
    return items
