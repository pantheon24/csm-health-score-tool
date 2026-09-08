"""展示模式用的虛構客戶資料。

⚠️ 全部為虛構資料，不含任何真實客戶資訊。
產品情境設定：一套 B2B SaaS「團隊協作與專案管理雲端平台」，按席位年繳訂閱。

所有日期都以「今天」為基準動態產生，所以這份 demo 不會隨時間過期。
"""

from datetime import date, timedelta

# ---------------------------------------------------------------- 導入里程碑範本

MILESTONE_TEMPLATE = [
    ("合約簽訂", "業務"),
    ("Kickoff 啟動會議", "CSM"),
    ("環境開通與帳號建立", "技術顧問"),
    ("管理員教育訓練", "CSM"),
    ("首批使用者上線", "客戶"),
    ("首次產生價值（TTV）", "CSM"),
    ("導入驗收結案", "CSM"),
]

DEFAULT_PLANNED_OFFSETS = [0, 7, 14, 28, 42, 60, 75]


def _iso(d):
    return d.isoformat()


def build_milestones(today, start_days_ago, actual_offsets, planned_offsets=None):
    """把里程碑範本展開成有日期與狀態的清單。

    actual_offsets：每個里程碑「實際完成」在導入起算第幾天，None 代表尚未完成。
    """
    planned_offsets = planned_offsets or DEFAULT_PLANNED_OFFSETS
    start = today - timedelta(days=start_days_ago)

    out = []
    pending_marked = False
    for (name, owner), planned_off, actual_off in zip(
        MILESTONE_TEMPLATE, planned_offsets, actual_offsets
    ):
        planned_date = start + timedelta(days=planned_off)
        if actual_off is not None:
            status = "完成"
            actual_date = _iso(start + timedelta(days=actual_off))
            delay = actual_off - planned_off
        else:
            actual_date = None
            delay = None
            if planned_date < today:
                status = "逾期"
            elif not pending_marked:
                status = "進行中"
                pending_marked = True
            else:
                status = "未開始"
        out.append({
            "name": name,
            "owner": owner,
            "planned": _iso(planned_date),
            "actual": actual_date,
            "status": status,
            "delay_days": delay,
        })
    return out


# ---------------------------------------------------------------- 客戶主檔
# renewal_in_days：距離合約到期還有幾天（負數代表已過期）
# actual_offsets：導入里程碑實際完成日（相對導入起算日）

CUSTOMERS = [
    {
        "id": "c01",
        "name": "晨曦餐飲集團",
        "industry": "連鎖餐飲",
        "plan": "Business",
        "stage": "成熟",
        "status": "active",
        "csm": "James",
        "prev_arr": 480_000,
        "arr": 480_000,
        "renewal_in_days": 77,
        "term_months": 12,
        "seats_purchased": 120,
        "seats_active": 38,
        "usage_30d": 5,
        "tickets_90d": 8,
        "urgent_tickets_90d": 3,
        "onboarding_pct": 100,
        "ttv_days": 96,
        "nps": 4,
        "csat": 2.6,
        "last_contact_days": 45,
        "tags": ["使用率崩落", "Champion 空缺", "續約風險"],
        "onboarding_start_days_ago": 660,
        "actual_offsets": [0, 9, 18, 35, 58, 96, 112],
        "renewal": {
            "stage": "未啟動",
            "amount": 480_000,
            "expansion": 0,
            "probability": 45,
            "next_action": "啟動 90 天續約流程：先做一次席位使用率診斷，帶著數據約營運總監",
            "next_action_in_days": 3,
            "note": "上一份合約是業務主導簽的，CSM 端沒有續約決策者的直接關係，需要先重建接觸點。",
        },
        "meetings": [
            {
                "days_ago": 96,
                "type": "QBR",
                "attendees": "周美玲（營運總監）、蔡宗翰（門市系統主管）",
                "summary": "Q2 業務回顧。客戶反映導入後排班流程並未如預期簡化，門市端抵抗明顯。",
                "commitments": [
                    {"item": "提供排班模板客製化教學", "owner": "CSM", "due_in_days": -60, "done": False},
                    {"item": "指派新的內部推廣窗口", "owner": "客戶", "due_in_days": -45, "done": False},
                ],
            },
            {
                "days_ago": 45,
                "type": "Check-in",
                "attendees": "蔡宗翰（門市系統主管）",
                "summary": "電話聯繫。得知蔡宗翰已轉調其他部門，內部無人接手推廣，此後未再有互動。",
                "commitments": [
                    {"item": "確認新的對接窗口是誰", "owner": "客戶", "due_in_days": -30, "done": False},
                ],
            },
        ],
        "contacts": [
            {"name": "周美玲", "title": "營運總監", "role": "決策者", "sentiment": "中立",
             "last_contact_days": 96, "note": "續約簽核者。只在 QBR 出現，日常不使用產品。"},
            {"name": "蔡宗翰", "title": "門市系統主管", "role": "Champion", "sentiment": "支持",
             "last_contact_days": 45, "note": "⚠️ 已轉調其他部門，Champion 實質空缺，這是目前最大的隱形風險。"},
            {"name": "林郁婷", "title": "旗艦店店長", "role": "日常使用者", "sentiment": "反對",
             "last_contact_days": 30, "note": "多次反映排班功能操作繁瑣，是門市端抵抗的意見領袖。"},
        ],
    },
    {
        "id": "c02",
        "name": "藍海物流",
        "industry": "倉儲物流",
        "plan": "Enterprise",
        "stage": "成熟",
        "status": "active",
        "csm": "王思涵",
        "prev_arr": 1_200_000,
        "arr": 1_440_000,
        "renewal_in_days": 192,
        "term_months": 12,
        "seats_purchased": 300,
        "seats_active": 268,
        "usage_30d": 45,
        "tickets_90d": 1,
        "urgent_tickets_90d": 0,
        "onboarding_pct": 100,
        "ttv_days": 41,
        "nps": 9,
        "csat": 4.6,
        "last_contact_days": 5,
        "tags": ["高價值", "可做案例研究", "已擴展"],
        "onboarding_start_days_ago": 780,
        "actual_offsets": [0, 6, 12, 25, 38, 41, 70],
        "renewal": {
            "stage": "未啟動",
            "amount": 1_440_000,
            "expansion": 240_000,
            "probability": 92,
            "next_action": "邀請擔任產品案例研究對象，並探詢明年是否再加 50 席",
            "next_action_in_days": 21,
            "note": "本期已從 300 席擴展至含跨區模組，續約風險低，重點放在擴展與轉介紹。",
        },
        "meetings": [
            {
                "days_ago": 20,
                "type": "QBR",
                "attendees": "許志明（資訊長）、鄭雅文（營運經理）",
                "summary": "Q3 業務回顧。展示配送排程平均縮短 22% 的 ROI 數據，客戶當場詢問跨區模組。",
                "commitments": [
                    {"item": "提供跨區模組報價與導入時程", "owner": "CSM", "due_in_days": -6, "done": True},
                ],
            },
        ],
        "contacts": [
            {"name": "許志明", "title": "資訊長", "role": "決策者", "sentiment": "支持",
             "last_contact_days": 20, "note": "預算決策者，重視可量化的 ROI 數字。"},
            {"name": "鄭雅文", "title": "營運經理", "role": "Champion", "sentiment": "支持",
             "last_contact_days": 5, "note": "內部推廣主力，主動辦過兩場內訓，是最理想的案例研究人選。"},
        ],
    },
    {
        "id": "c03",
        "name": "恆星生技",
        "industry": "生技製藥",
        "plan": "Enterprise",
        "stage": "成熟",
        "status": "active",
        "csm": "王思涵",
        "prev_arr": 960_000,
        "arr": 960_000,
        "renewal_in_days": 92,
        "term_months": 12,
        "seats_purchased": 250,
        "seats_active": 205,
        "usage_30d": 32,
        "tickets_90d": 3,
        "urgent_tickets_90d": 0,
        "onboarding_pct": 100,
        "ttv_days": 55,
        "nps": 9,
        "csat": 4.2,
        "last_contact_days": 12,
        "tags": ["穩定", "法遵需求高"],
        "onboarding_start_days_ago": 640,
        "actual_offsets": [0, 8, 16, 30, 45, 55, 80],
        "renewal": {
            "stage": "未啟動",
            "amount": 960_000,
            "expansion": 0,
            "probability": 85,
            "next_action": "下週進入 90 天窗口，先確認今年度稽核報表需求是否有變",
            "next_action_in_days": 2,
            "note": "客戶對法遵稽核報表依賴度高，是很強的留存黏著點。",
        },
        "meetings": [
            {
                "days_ago": 35,
                "type": "QBR",
                "attendees": "黃振宇（研發處長）、李佩珊（品保經理）",
                "summary": "Q3 業務回顧。稽核報表功能獲得高度肯定，提出希望增加電子簽核軌跡。",
                "commitments": [
                    {"item": "把電子簽核軌跡需求送進產品路線圖評估", "owner": "CSM", "due_in_days": 10, "done": False},
                ],
            },
        ],
        "contacts": [
            {"name": "黃振宇", "title": "研發處長", "role": "決策者", "sentiment": "支持",
             "last_contact_days": 35, "note": "續約簽核者。"},
            {"name": "李佩珊", "title": "品保經理", "role": "Champion", "sentiment": "支持",
             "last_contact_days": 12, "note": "每日重度使用者，稽核季節時使用量會翻倍。"},
        ],
    },
    {
        "id": "c04",
        "name": "沐光文創",
        "industry": "文創設計",
        "plan": "Standard",
        "stage": "導入",
        "status": "active",
        "csm": "李昀真",
        "prev_arr": 0,
        "arr": 180_000,
        "renewal_in_days": 270,
        "term_months": 12,
        "seats_purchased": 40,
        "seats_active": 12,
        "usage_30d": 9,
        "tickets_90d": 4,
        "urgent_tickets_90d": 1,
        "onboarding_pct": 55,
        "ttv_days": None,
        "nps": None,
        "csat": 3.8,
        "last_contact_days": 3,
        "tags": ["新客戶", "導入中"],
        "onboarding_start_days_ago": 38,
        "actual_offsets": [0, 6, 15, 33, None, None, None],
        "renewal": {
            "stage": "未啟動",
            "amount": 180_000,
            "expansion": 0,
            "probability": 70,
            "next_action": "導入尚未完成，續約評估暫緩；先確保 60 天內達成首次價值",
            "next_action_in_days": 22,
            "note": "新簽客戶，本期不計入 NRR 分母。",
        },
        "meetings": [
            {
                "days_ago": 3,
                "type": "導入進度會",
                "attendees": "何冠廷（設計總監）",
                "summary": "管理員訓練已完成，但首批使用者尚未實際上線，卡在專案範本還沒定義完。",
                "commitments": [
                    {"item": "協助定義 3 個常用專案範本", "owner": "CSM", "due_in_days": 4, "done": False},
                    {"item": "指定首批 12 位使用者名單", "owner": "客戶", "due_in_days": 7, "done": False},
                ],
            },
        ],
        "contacts": [
            {"name": "何冠廷", "title": "設計總監", "role": "決策者", "sentiment": "支持",
             "last_contact_days": 3, "note": "採購決策者，同時也是實際使用者，導入期配合度高。"},
            {"name": "吳語婕", "title": "專案管理師", "role": "日常使用者", "sentiment": "中立",
             "last_contact_days": 9, "note": "尚未熟悉產品，是潛在 Champion 培養對象。"},
        ],
    },
    {
        "id": "c05",
        "name": "鐵砧工業",
        "industry": "金屬製造",
        "plan": "Business",
        "stage": "成熟",
        "status": "active",
        "csm": "James",
        "prev_arr": 600_000,
        "arr": 480_000,
        "renewal_in_days": 34,
        "term_months": 12,
        "seats_purchased": 150,
        "seats_active": 41,
        "usage_30d": 6,
        "tickets_90d": 11,
        "urgent_tickets_90d": 4,
        "onboarding_pct": 80,
        "ttv_days": 138,
        "nps": 3,
        "csat": 2.4,
        "last_contact_days": 28,
        "tags": ["已縮減席位", "工單量高", "高流失風險"],
        "onboarding_start_days_ago": 700,
        "actual_offsets": [0, 12, 26, 55, 90, 138, None],
        "renewal": {
            "stage": "需求確認",
            "amount": 480_000,
            "expansion": -120_000,
            "probability": 35,
            "next_action": "34 天內到期。安排高層介入會議（EBR），帶改善承諾表出席",
            "next_action_in_days": 2,
            "note": "上期已從 150 席縮減到實際付費 120 席，客戶明確表達再降席位的意圖。導入驗收至今未結案。",
        },
        "meetings": [
            {
                "days_ago": 62,
                "type": "QBR",
                "attendees": "陳國強（廠務副總）、劉建志（IT 主管）",
                "summary": "Q2 業務回顧。客戶列出 4 項未解決的整合問題，對支援回應速度不滿。",
                "commitments": [
                    {"item": "ERP 介接問題於 30 天內收斂", "owner": "CSM", "due_in_days": -32, "done": False},
                    {"item": "提供專屬技術對接窗口", "owner": "CSM", "due_in_days": -40, "done": True},
                ],
            },
            {
                "days_ago": 28,
                "type": "Check-in",
                "attendees": "劉建志（IT 主管）",
                "summary": "IT 主管表示 ERP 介接仍未解決，現場人員多改回用 Excel 作業。",
                "commitments": [
                    {"item": "升級為跨部門處理並提供時程表", "owner": "CSM", "due_in_days": -14, "done": False},
                ],
            },
        ],
        "contacts": [
            {"name": "陳國強", "title": "廠務副總", "role": "決策者", "sentiment": "反對",
             "last_contact_days": 62, "note": "⚠️ 明確表達成本壓力，是主張縮減或終止的一方。"},
            {"name": "劉建志", "title": "IT 主管", "role": "技術窗口", "sentiment": "中立",
             "last_contact_days": 28, "note": "願意協助但受限於 ERP 介接問題未解，立場正在轉為消極。"},
            {"name": "楊書豪", "title": "生產課長", "role": "日常使用者", "sentiment": "反對",
             "last_contact_days": 75, "note": "現場已回退到 Excel 作業，實質流失的起點。"},
        ],
    },
    {
        "id": "c06",
        "name": "雲頂金融科技",
        "industry": "金融科技",
        "plan": "Enterprise",
        "stage": "續約中",
        "status": "active",
        "csm": "王思涵",
        "prev_arr": 1_500_000,
        "arr": 1_500_000,
        "renewal_in_days": 26,
        "term_months": 12,
        "seats_purchased": 400,
        "seats_active": 351,
        "usage_30d": 38,
        "tickets_90d": 5,
        "urgent_tickets_90d": 1,
        "onboarding_pct": 100,
        "ttv_days": 48,
        "nps": 8,
        "csat": 4.1,
        "last_contact_days": 2,
        "tags": ["最大客戶", "續約談判中", "有擴展機會"],
        "onboarding_start_days_ago": 620,
        "actual_offsets": [0, 5, 11, 24, 36, 48, 68],
        "renewal": {
            "stage": "提案已送",
            "amount": 1_500_000,
            "expansion": 180_000,
            "probability": 78,
            "next_action": "採購部要求比價說明，需補一份與競品的功能對照與 ROI 佐證",
            "next_action_in_days": 4,
            "note": "業務面沒問題，卡點在採購流程要求的比價程序。已提出加購資安模組的擴展方案。",
        },
        "meetings": [
            {
                "days_ago": 18,
                "type": "EBR",
                "attendees": "張立群（副總經理）、彭思穎（數位轉型辦公室主任）",
                "summary": "高層業務回顧。展示年度使用成效與合規稽核價值，副總表態支持續約。",
                "commitments": [
                    {"item": "提供資安模組加購方案", "owner": "CSM", "due_in_days": -10, "done": True},
                ],
            },
            {
                "days_ago": 2,
                "type": "Check-in",
                "attendees": "彭思穎（數位轉型辦公室主任）",
                "summary": "採購部要求提供比價依據，Champion 已協助爭取到本月底前完成簽核。",
                "commitments": [
                    {"item": "補件：競品功能對照表 + ROI 佐證", "owner": "CSM", "due_in_days": 4, "done": False},
                ],
            },
        ],
        "contacts": [
            {"name": "張立群", "title": "副總經理", "role": "決策者", "sentiment": "支持",
             "last_contact_days": 18, "note": "最終簽核者，已在 EBR 表態支持。"},
            {"name": "彭思穎", "title": "數位轉型辦公室主任", "role": "Champion", "sentiment": "支持",
             "last_contact_days": 2, "note": "強力 Champion，主動協助推進內部採購流程。"},
            {"name": "郭俊傑", "title": "採購經理", "role": "技術窗口", "sentiment": "中立",
             "last_contact_days": 6, "note": "流程守門人，只在意比價程序是否完備，不涉入產品價值判斷。"},
        ],
    },
    {
        "id": "c07",
        "name": "綠芽教育",
        "industry": "教育培訓",
        "plan": "Standard",
        "stage": "採用",
        "status": "active",
        "csm": "李昀真",
        "prev_arr": 144_000,
        "arr": 216_000,
        "renewal_in_days": 136,
        "term_months": 12,
        "seats_purchased": 60,
        "seats_active": 44,
        "usage_30d": 22,
        "tickets_90d": 2,
        "urgent_tickets_90d": 0,
        "onboarding_pct": 100,
        "ttv_days": 35,
        "nps": 7,
        "csat": 4.0,
        "last_contact_days": 9,
        "tags": ["已擴展", "採用中"],
        "onboarding_start_days_ago": 300,
        "actual_offsets": [0, 5, 10, 22, 30, 35, 58],
        "renewal": {
            "stage": "未啟動",
            "amount": 216_000,
            "expansion": 72_000,
            "probability": 80,
            "next_action": "本季 QBR 展示採用成效，探詢是否再擴增到 80 席",
            "next_action_in_days": 30,
            "note": "本期已從 40 席擴增到 60 席，成長動能良好。",
        },
        "meetings": [
            {
                "days_ago": 9,
                "type": "Check-in",
                "attendees": "曾慧君（教務主任）",
                "summary": "月度聯繫。分校導入順利，詢問是否有跨校區報表功能。",
                "commitments": [
                    {"item": "示範跨校區彙總報表設定", "owner": "CSM", "due_in_days": 5, "done": False},
                ],
            },
        ],
        "contacts": [
            {"name": "曾慧君", "title": "教務主任", "role": "Champion", "sentiment": "支持",
             "last_contact_days": 9, "note": "推動分校導入的主要力量。"},
            {"name": "簡文彥", "title": "執行長", "role": "決策者", "sentiment": "中立",
             "last_contact_days": 75, "note": "尚未直接接觸過產品價值簡報，續約前需安排一次。"},
        ],
    },
    {
        "id": "c08",
        "name": "潮汐電商",
        "industry": "電子商務",
        "plan": "Business",
        "stage": "採用",
        "status": "active",
        "csm": "James",
        "prev_arr": 360_000,
        "arr": 360_000,
        "renewal_in_days": 59,
        "term_months": 12,
        "seats_purchased": 100,
        "seats_active": 58,
        "usage_30d": 15,
        "tickets_90d": 6,
        "urgent_tickets_90d": 1,
        "onboarding_pct": 95,
        "ttv_days": 72,
        "nps": 7,
        "csat": 3.4,
        "last_contact_days": 18,
        "tags": ["席位閒置", "待追蹤"],
        "onboarding_start_days_ago": 420,
        "actual_offsets": [0, 9, 20, 40, 60, 72, None],
        "renewal": {
            "stage": "需求確認",
            "amount": 360_000,
            "expansion": 0,
            "probability": 65,
            "next_action": "59 天到期。先處理 42 席閒置問題，避免客戶用「用不到」當降額理由",
            "next_action_in_days": 5,
            "note": "100 席只有 58 席活躍，是續約談判時最容易被拿來砍價的破口。",
        },
        "meetings": [
            {
                "days_ago": 18,
                "type": "Check-in",
                "attendees": "羅心蕾（電商營運經理）",
                "summary": "月度聯繫。客服團隊使用率高，但倉儲與行銷團隊幾乎沒登入。",
                "commitments": [
                    {"item": "針對倉儲團隊辦一場情境式教育訓練", "owner": "CSM", "due_in_days": 3, "done": False},
                ],
            },
        ],
        "contacts": [
            {"name": "羅心蕾", "title": "電商營運經理", "role": "Champion", "sentiment": "支持",
             "last_contact_days": 18, "note": "客服團隊的推動者，但影響力沒有延伸到其他部門。"},
            {"name": "邱柏宏", "title": "營運副總", "role": "決策者", "sentiment": "中立",
             "last_contact_days": 110, "note": "⚠️ 續約決策者，但已超過 3 個月沒有互動。"},
        ],
    },
    {
        "id": "c09",
        "name": "磐石營造",
        "industry": "營建工程",
        "plan": "Business",
        "stage": "導入",
        "status": "active",
        "csm": "李昀真",
        "prev_arr": 0,
        "arr": 420_000,
        "renewal_in_days": 218,
        "term_months": 12,
        "seats_purchased": 110,
        "seats_active": 26,
        "usage_30d": 4,
        "tickets_90d": 7,
        "urgent_tickets_90d": 2,
        "onboarding_pct": 35,
        "ttv_days": None,
        "nps": None,
        "csat": 3.0,
        "last_contact_days": 1,
        "tags": ["新客戶", "導入逾期", "需要輔導"],
        "onboarding_start_days_ago": 86,
        "actual_offsets": [0, 11, 29, None, None, None, None],
        "renewal": {
            "stage": "未啟動",
            "amount": 420_000,
            "expansion": 0,
            "probability": 55,
            "next_action": "導入嚴重落後（第 86 天仍未完成管理員訓練），需要重擬導入計畫",
            "next_action_in_days": 1,
            "note": "新簽客戶，本期不計入 NRR 分母。導入卡關是第一年流失最主要的原因，需優先處理。",
        },
        "meetings": [
            {
                "days_ago": 1,
                "type": "導入進度會",
                "attendees": "王國賓（工程部經理）、施明宏（IT 專員）",
                "summary": "客戶端工地主任排不出訓練時間，兩次改期。IT 專員為唯一窗口但無決策權。",
                "commitments": [
                    {"item": "改為錄製 20 分鐘非同步訓練影片，降低參與門檻", "owner": "CSM", "due_in_days": 6, "done": False},
                    {"item": "向工程部經理爭取一場 30 分鐘的高層宣達", "owner": "CSM", "due_in_days": 9, "done": False},
                ],
            },
            {
                "days_ago": 30,
                "type": "導入進度會",
                "attendees": "施明宏（IT 專員）",
                "summary": "環境開通完成，但管理員訓練第二次改期，導入時程開始落後。",
                "commitments": [
                    {"item": "確認訓練時間", "owner": "客戶", "due_in_days": -16, "done": False},
                ],
            },
        ],
        "contacts": [
            {"name": "王國賓", "title": "工程部經理", "role": "決策者", "sentiment": "中立",
             "last_contact_days": 1, "note": "簽約決策者，但導入期幾乎不參與，需要拉回來背書。"},
            {"name": "施明宏", "title": "IT 專員", "role": "技術窗口", "sentiment": "支持",
             "last_contact_days": 1, "note": "配合度高但層級低，推不動工地端。目前無真正的 Champion。"},
        ],
    },
    {
        "id": "c10",
        "name": "星鏈半導體",
        "industry": "半導體",
        "plan": "Enterprise",
        "stage": "成熟",
        "status": "active",
        "csm": "王思涵",
        "prev_arr": 1_800_000,
        "arr": 2_160_000,
        "renewal_in_days": 177,
        "term_months": 12,
        "seats_purchased": 500,
        "seats_active": 462,
        "usage_30d": 51,
        "tickets_90d": 2,
        "urgent_tickets_90d": 0,
        "onboarding_pct": 100,
        "ttv_days": 29,
        "nps": 10,
        "csat": 4.8,
        "last_contact_days": 7,
        "tags": ["最佳實踐客戶", "已擴展", "可做推薦人"],
        "onboarding_start_days_ago": 900,
        "actual_offsets": [0, 4, 9, 18, 25, 29, 52],
        "renewal": {
            "stage": "未啟動",
            "amount": 2_160_000,
            "expansion": 360_000,
            "probability": 95,
            "next_action": "邀請加入客戶顧問委員會（CAB），並洽談集團其他事業處的轉介紹",
            "next_action_in_days": 14,
            "note": "本期擴展 20%，是最健康的客戶。重點從留存轉為擴展與品牌背書。",
        },
        "meetings": [
            {
                "days_ago": 7,
                "type": "QBR",
                "attendees": "沈冠霖（製造資訊部協理）、方詩涵（專案辦公室主管）",
                "summary": "Q3 業務回顧。跨廠專案協作全面上線，客戶主動詢問集團其他事業處導入可能。",
                "commitments": [
                    {"item": "安排集團其他事業處的導入說明會", "owner": "CSM", "due_in_days": 12, "done": False},
                ],
            },
        ],
        "contacts": [
            {"name": "沈冠霖", "title": "製造資訊部協理", "role": "決策者", "sentiment": "支持",
             "last_contact_days": 7, "note": "強力支持者，願意對集團內部推薦。"},
            {"name": "方詩涵", "title": "專案辦公室主管", "role": "Champion", "sentiment": "支持",
             "last_contact_days": 7, "note": "產品重度使用者，自行製作了內部使用指南。"},
        ],
    },
    {
        "id": "c11",
        "name": "微風旅遊",
        "industry": "旅遊服務",
        "plan": "Standard",
        "stage": "續約中",
        "status": "active",
        "csm": "James",
        "prev_arr": 240_000,
        "arr": 144_000,
        "renewal_in_days": 14,
        "term_months": 12,
        "seats_purchased": 50,
        "seats_active": 9,
        "usage_30d": 2,
        "tickets_90d": 9,
        "urgent_tickets_90d": 3,
        "onboarding_pct": 70,
        "ttv_days": None,
        "nps": 2,
        "csat": 2.1,
        "last_contact_days": 62,
        "tags": ["緊急", "已縮減席位", "極高流失風險"],
        "onboarding_start_days_ago": 380,
        "actual_offsets": [0, 14, 33, 71, None, None, None],
        "renewal": {
            "stage": "議價中",
            "amount": 144_000,
            "expansion": -96_000,
            "probability": 20,
            "next_action": "14 天到期且 62 天未聯繫。今日必須發起挽救行動，先取得一通電話",
            "next_action_in_days": 0,
            "note": "50 席只剩 9 席活躍，從未達成首次價值（TTV 未完成）。這是典型的「導入失敗 → 使用率崩落 → 流失」路徑。",
        },
        "meetings": [
            {
                "days_ago": 62,
                "type": "Check-in",
                "attendees": "許雅琪（行政主管）",
                "summary": "客戶表示疫情後組織縮編，原本規劃的使用情境已不存在，對續約態度保留。",
                "commitments": [
                    {"item": "提出降階方案或使用情境重新設計", "owner": "CSM", "due_in_days": -45, "done": False},
                ],
            },
        ],
        "contacts": [
            {"name": "許雅琪", "title": "行政主管", "role": "技術窗口", "sentiment": "中立",
             "last_contact_days": 62, "note": "唯一聯繫窗口，非決策者。"},
            {"name": "（未知）", "title": "總經理", "role": "決策者", "sentiment": "未知",
             "last_contact_days": None, "note": "⚠️ 從未接觸過決策者，這是最大的結構性問題。"},
        ],
    },
    {
        "id": "c12",
        "name": "方舟醫療",
        "industry": "醫療器材",
        "plan": "Enterprise",
        "stage": "採用",
        "status": "active",
        "csm": "李昀真",
        "prev_arr": 840_000,
        "arr": 900_000,
        "renewal_in_days": 107,
        "term_months": 12,
        "seats_purchased": 200,
        "seats_active": 141,
        "usage_30d": 28,
        "tickets_90d": 4,
        "urgent_tickets_90d": 1,
        "onboarding_pct": 100,
        "ttv_days": 62,
        "nps": 9,
        "csat": 3.9,
        "last_contact_days": 11,
        "tags": ["採用中", "有擴展空間"],
        "onboarding_start_days_ago": 480,
        "actual_offsets": [0, 7, 15, 32, 50, 62, 88],
        "renewal": {
            "stage": "未啟動",
            "amount": 900_000,
            "expansion": 60_000,
            "probability": 82,
            "next_action": "安排 Q4 QBR，帶著業務部門的採用缺口數據談擴展",
            "next_action_in_days": 18,
            "note": "研發與品保部門採用良好，業務部門尚未導入，是明確的擴展空間。",
        },
        "meetings": [
            {
                "days_ago": 11,
                "type": "Check-in",
                "attendees": "潘俊安（品保部經理）",
                "summary": "月度聯繫。品保流程已全面上線，業務部門仍在觀望。",
                "commitments": [
                    {"item": "準備業務部門適用的情境範例", "owner": "CSM", "due_in_days": 8, "done": False},
                ],
            },
        ],
        "contacts": [
            {"name": "潘俊安", "title": "品保部經理", "role": "Champion", "sentiment": "支持",
             "last_contact_days": 11, "note": "品保端的推動者。"},
            {"name": "戴俊雄", "title": "營運長", "role": "決策者", "sentiment": "支持",
             "last_contact_days": 45, "note": "支持擴大導入，但要求先看到現有部門的量化成效。"},
        ],
    },
    # ---- 已流失客戶（只計入 NRR/GRR 與流失分析，不出現在日常清單） ----
    {
        "id": "c13",
        "name": "光影廣告",
        "industry": "廣告行銷",
        "plan": "Standard",
        "stage": "已流失",
        "status": "churned",
        "csm": "James",
        "prev_arr": 180_000,
        "arr": 0,
        "renewal_in_days": -66,
        "term_months": 12,
        "seats_purchased": 45,
        "seats_active": 0,
        "usage_30d": 0,
        "tickets_90d": 0,
        "urgent_tickets_90d": 0,
        "onboarding_pct": 60,
        "ttv_days": None,
        "nps": 3,
        "csat": 2.2,
        "last_contact_days": 66,
        "tags": ["已流失"],
        "churn_reason": "導入未完成即到期，客戶認為未產生價值",
        "onboarding_start_days_ago": 430,
        "actual_offsets": [0, 15, 40, None, None, None, None],
        "renewal": {
            "stage": "已流失",
            "amount": 0,
            "expansion": -180_000,
            "probability": 0,
            "next_action": "已結案。流失原因已回饋產品與導入流程",
            "next_action_in_days": None,
            "note": "流失主因：導入停在第 40 天就失去客戶端窗口，從未達成首次價值。",
        },
        "meetings": [],
        "contacts": [],
    },
    {
        "id": "c14",
        "name": "大河紡織",
        "industry": "紡織製造",
        "plan": "Business",
        "stage": "已流失",
        "status": "churned",
        "csm": "王思涵",
        "prev_arr": 300_000,
        "arr": 0,
        "renewal_in_days": -20,
        "term_months": 12,
        "seats_purchased": 80,
        "seats_active": 0,
        "usage_30d": 0,
        "tickets_90d": 0,
        "urgent_tickets_90d": 0,
        "onboarding_pct": 100,
        "ttv_days": 110,
        "nps": 5,
        "csat": 3.1,
        "last_contact_days": 20,
        "tags": ["已流失"],
        "churn_reason": "母公司統一採購政策，改用集團指定系統",
        "onboarding_start_days_ago": 750,
        "actual_offsets": [0, 10, 22, 48, 80, 110, 140],
        "renewal": {
            "stage": "已流失",
            "amount": 0,
            "expansion": -300_000,
            "probability": 0,
            "next_action": "已結案。屬不可控流失（集團政策），列入不可控 churn 類別",
            "next_action_in_days": None,
            "note": "健康分數一直是綠燈，流失與產品體驗無關，屬外部不可控因素。",
        },
        "meetings": [],
        "contacts": [],
    },
]


def load_customers(today=None):
    """回傳展開好日期的客戶資料（deep copy，不動到原始常數）。"""
    import copy

    today = today or date.today()
    out = []
    for spec in CUSTOMERS:
        c = copy.deepcopy(spec)
        c["renewal_date"] = _iso(today + timedelta(days=c["renewal_in_days"]))
        c["contract_start"] = _iso(
            today + timedelta(days=c["renewal_in_days"] - 30 * c["term_months"])
        )
        c["last_contact_date"] = _iso(today - timedelta(days=c["last_contact_days"]))
        c["milestones"] = build_milestones(
            today, c["onboarding_start_days_ago"], c["actual_offsets"]
        )
        for m in c["meetings"]:
            m["date"] = _iso(today - timedelta(days=m["days_ago"]))
            for cm in m["commitments"]:
                cm["due"] = _iso(today + timedelta(days=cm["due_in_days"]))
                cm["overdue"] = (not cm["done"]) and cm["due_in_days"] < 0
        r = c["renewal"]
        r["next_action_date"] = (
            _iso(today + timedelta(days=r["next_action_in_days"]))
            if r["next_action_in_days"] is not None
            else None
        )
        out.append(c)
    return out
