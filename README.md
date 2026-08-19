# 客戶健康分數＋續約風險預警工具

CSM 求職作品：上傳客戶資料 CSV，自動算出健康分數、續約風險燈號，並產生風險說明與建議行動。

## 本機執行

```bash
# 第一次使用，先安裝套件（已經做過可跳過）
./venv/Scripts/python.exe -m pip install -r requirements.txt

# 啟動
./venv/Scripts/python.exe -m streamlit run app.py
```

開啟瀏覽器 http://localhost:8501，上傳 `demo-customers.csv` 就能看到完整結果。

## 設定真實 AI（Claude API）生成風險說明

目前沒有設定金鑰時，系統會自動用內建的規則引擎生成風險說明（已驗證可正常運作）。若要改用真的 Claude API：

1. 到 https://console.anthropic.com 申請一組 API 金鑰
2. 在本機執行前，設定環境變數：
   ```bash
   export ANTHROPIC_API_KEY=你的金鑰
   ```
3. 重新啟動 `streamlit run app.py`，畫面上的「使用真實 AI」開關會自動變成可勾選

呼叫 Claude API 會依用量產生極少量費用（單次生成約新台幣不到 1 元）。

## 部署成公開連結（Streamlit Community Cloud，免費）

1. 把這個資料夾推上 GitHub（可以是 private repo）
2. 到 https://share.streamlit.io 用 GitHub 帳號登入，選擇這個 repo，指定 `app.py` 為進入檔案
3. 在 Streamlit Cloud 後台的 "Secrets" 設定裡加入：
   ```toml
   ANTHROPIC_API_KEY = "你的金鑰"
   ```
   （金鑰只存在 Streamlit 伺服器端，不會出現在任何前端程式碼或公開連結裡）
4. 部署完成後會拿到一個 `https://xxx.streamlit.app` 的公開連結，可以直接放履歷

## 檔案說明

- `app.py`：主程式
- `csv-template.csv`：CSV 欄位範本
- `demo-customers.csv`：24 筆虛構示範客戶資料（涵蓋高中低風險與續約風險情境）
- `plan.md`：這個作品的規劃紀錄
