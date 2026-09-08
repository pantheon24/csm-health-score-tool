"""無頭煙霧測試：用 Streamlit 官方 AppTest 跑過每一頁與每一位客戶，確認沒有例外。

執行：./venv/Scripts/python.exe smoke_test.py
"""

from streamlit.testing.v1 import AppTest

import demo_data

PAGES = ["總覽", "客戶列表", "客戶詳情", "續約管理", "指標字典"]
fails = 0


def new_app():
    return AppTest.from_file("app.py", default_timeout=90).run()


for page in PAGES:
    at = new_app()
    at.session_state["nav"] = page
    at.run()
    ok = not at.exception
    fails += 0 if ok else 1
    print(f"[{'PASS' if ok else 'FAIL'}] {page}"
          f"（markdown={len(at.markdown)} metric={len(at.metric)} dataframe={len(at.dataframe)}）")
    for e in at.exception:
        print("    ", e.value)

at = new_app()
detail_fails = 0
for c in demo_data.CUSTOMERS:
    at.session_state["nav"] = "客戶詳情"
    at.session_state["selected_id"] = c["id"]
    at.run()
    if at.exception:
        detail_fails += 1
        print(f"[FAIL] 客戶詳情 {c['name']}：{at.exception[0].value}")
fails += detail_fails
print(f"[{'PASS' if not detail_fails else 'FAIL'}] "
      f"{len(demo_data.CUSTOMERS)} 位客戶的詳情頁全部渲染")

print("\n總結：" + ("全部通過" if fails == 0 else f"{fails} 項失敗"))
raise SystemExit(1 if fails else 0)
