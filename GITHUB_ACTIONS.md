# 雲端排程設定說明（GitHub Actions）

電腦關機也會照常執行。三個 workflow 放在 `.github/workflows/`，產出會自動 commit 回 repo。

| Workflow | 檔案 | 台灣時間 | 做什麼 | 用到 Claude |
|---|---|---|---|---|
| 房市新聞摘要 | news.yml | 每週一、四 08:00 | 產生 `reports/news_YYYY-MM-DD.md` | 是 |
| 實價登錄指標 | data.yml | 每月 1、11、21 日 09:00，隔天再補跑一次 | 自動下載本期實價登錄，更新 `data/district_metrics.csv` | 否，純 Python |
| 總經與建照使照指標 | indicators.yml | 每月 5、25 日 09:00 | 更新 `data/macro_supply.csv`，產生 `reports/indicators_YYYY-MM-DD.md` | 是 |

實價登錄多排一次隔天，是怕內政部當天較晚才更新：如果早上抓到的還是上一期，腳本會直接跳過，隔天那次再補上新的一期。

## 一次性設定

### 1. 建立私人 repo 並推上去

1. 到 GitHub 右上角「+」→ New repository，名稱例如 `taiwan-real-estate-tracker`，選 **Private**，其他選項都不要勾（不要自動產生 README）。
2. 建議先設定 commit 用的 email，避免日後公開時露出個人信箱：GitHub → Settings → Emails，勾選「Keep my email addresses private」，複製下面那組 `...@users.noreply.github.com`。
3. 在 PowerShell 執行（把網址和 email 換成你的）：

   ```powershell
   cd C:\Real-estate
   git init -b main
   git config user.name "你的名字"
   git config user.email "12345678+帳號@users.noreply.github.com"
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/帳號/taiwan-real-estate-tracker.git
   git push -u origin main
   ```

   `data/raw/`（原始 zip）和 `logs/` 不會被推上去；`reports/`、`data/*.csv` 會。

### 2. 產生 Claude 訂閱制 token

在 PowerShell 執行：

```powershell
claude setup-token
```

依畫面完成登入後會印出一串 token，複製起來。這串 token 等同你的帳號權限，不要貼到任何檔案或聊天裡。

### 3. 把 token 放進 repo 的 Secrets

repo 頁面 → Settings → Secrets and variables → Actions → New repository secret

- Name：`CLAUDE_CODE_OAUTH_TOKEN`
- Secret：貼上剛剛的 token

### 4. 允許 workflow 寫回 repo

repo → Settings → Actions → General → 最下面 Workflow permissions，選 **Read and write permissions** → Save。

### 5. 設定 email 寄送

新聞和指標跑完後，會用 Gmail 把當天的報告寄出（內文是排版後的報告，另附原始 .md 檔）。

1. 寄件用的 Gmail 要先開啟兩步驟驗證：Google 帳戶 → 安全性 → 兩步驟驗證。
2. 建立應用程式密碼：Google 帳戶 → 安全性 → 應用程式密碼（或直接搜尋「應用程式密碼」），名稱填 `GitHub Actions`，會得到一組 16 碼密碼。這不是 Gmail 登入密碼，只能拿來寄信，不用時可以隨時撤銷。
3. 在 repo 的 Settings → Secrets and variables → Actions 新增三個 Secret：

   | Name | 內容 |
   |---|---|
   | `MAIL_USERNAME` | 寄件的 Gmail 地址 |
   | `MAIL_PASSWORD` | 上一步的 16 碼應用程式密碼（空格可以不打） |
   | `MAIL_TO` | 收件地址，可以和寄件相同；多個地址用逗號分隔 |

收件地址放在 Secret 而不是寫在 workflow 裡，是為了 repo 日後公開時不會露出 email。

## 手動測試

repo 頁面 → Actions 分頁 → 左邊選一個 workflow → 右邊「Run workflow」。建議依序測：

1. **實價登錄指標**：最快、不花 Claude 額度。綠勾代表成功；這期資料已經在 csv 裡的話，log 會顯示「已處理過，跳過」，這也是正常的。
2. **房市新聞摘要**：跑完後 `reports/` 應該多一份當天的報告。
3. **總經與建照使照指標**。

## 排錯

- **下載的不是 zip**：GitHub 的機器在美國，若內政部網站擋國外連線就會出現這個錯誤。這時實價登錄改回本機處理：手動下載 zip 放進 `data\raw\`，執行 `run_data.ps1`，再把 `data/district_metrics.csv` commit 上去。
- **Claude 驗證失敗**：token 可能過期或打錯，重新執行 `claude setup-token`，更新 Secret。
- **push 被拒（permission denied）**：檢查第 4 步的 Workflow permissions。
- **「寄送報告到 email」失敗**：報告已經 commit 進 repo，只是沒寄出。通常是應用程式密碼錯誤（log 會出現 `Invalid login` 或 `535`），重新產生一組更新 `MAIL_PASSWORD` 即可。
- **排程時間不準**：GitHub 的排程常延遲幾分鐘到幾十分鐘，屬於正常現象。
- **排程停了**：公開 repo 若 60 天沒有任何 commit，GitHub 會自動停用排程；私人 repo 沒有這個限制。workflow 本身會定期 commit，通常不會遇到。

## 和本機排程的關係

本機的 `run_*.ps1` 和 [SCHEDULE.md](SCHEDULE.md) 還是可以用，例如想臨時多跑一次。但不要兩邊同時排程：Actions 啟用後，請把 Windows 工作排程器裡的三個工作停用，以免重複產生報告，或本機和雲端的資料不同步。本機手動跑完要先 `git pull` 再 commit。
