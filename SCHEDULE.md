# 排程設定說明（Windows 工作排程器）

> 主要排程已改用 GitHub Actions（關機也會執行），見 [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md)。這份說明保留給想在本機執行的情況；雲端排程啟用後，請不要同時在本機排程。

三支腳本都用 Windows 內建的「工作排程器」手動建立，以下是每支的設定方式。

| 腳本 | 用途 | 執行時間 |
|---|---|---|
| run_news.ps1 | 整理近 3 天房市新聞 | 每週一、四 08:00 |
| run_data.ps1 | 處理實價登錄 zip，更新 district_metrics.csv | 每月 1、11、21 日 09:00 |
| run_indicators.ps1 | 更新總經與建照使照指標 | 每月 5、25 日 09:00 |

## 建立步驟

1. 按 Win 鍵搜尋「工作排程器」並開啟。
2. 右側點「建立工作」（不要用「建立基本工作」，選項比較少）。
3. **一般** 分頁
   - 名稱：例如 `RealEstate-News`、`RealEstate-Data`、`RealEstate-Indicators`
   - 選「只在使用者登入時執行」最單純；若要沒登入也能跑，改選「不論使用者登入與否均執行」，儲存時會要求輸入 Windows 密碼。
4. **觸發程序** 分頁 → 新增
   - run_news.ps1：選「每週」，勾選「星期一」「星期四」，開始時間 08:00:00
   - run_data.ps1：選「每月」，月份選「全部」，日期勾選 1、11、21，開始時間 09:00:00
   - run_indicators.ps1：選「每月」，月份選「全部」，日期勾選 5、25，開始時間 09:00:00
5. **動作** 分頁 → 新增，動作選「啟動程式」

   | 工作 | 程式或指令碼 | 新增引數 |
   |---|---|---|
   | News | `powershell.exe` | `-NoProfile -ExecutionPolicy Bypass -File C:\Real-estate\run_news.ps1` |
   | Data | `powershell.exe` | `-NoProfile -ExecutionPolicy Bypass -File C:\Real-estate\run_data.ps1` |
   | Indicators | `powershell.exe` | `-NoProfile -ExecutionPolicy Bypass -File C:\Real-estate\run_indicators.ps1` |

   「開始位置」可以填 `C:\Real-estate`（腳本第一行也會切換過去，填不填都可以）。
6. **條件** 分頁：筆電的話建議取消勾選「只有在電腦使用 AC 電源時才啟動工作」。
7. **設定** 分頁：建議勾選「錯過排定的開始時間後，盡快執行工作」，這樣早上沒開機的話，開機後會補跑。

## 測試與排錯

- 建好後在工作上按右鍵 →「執行」，先手動跑一次。
- 每次執行的輸出會存在 `logs\` 資料夾，檔名像 `news_2026-10-06_0800.log`，最後一行會寫結束碼（0 代表正常結束）。
- 若 log 是空的或找不到 claude：腳本裡用的是完整路徑 `C:\Users\User\.local\bin\claude.exe`，若之後重裝 Claude Code 導致位置改變，在 PowerShell 執行 `(Get-Command claude).Source` 查新路徑，再更新三支腳本。
- 若 log 顯示權限被拒：確認 Claude Code 已經在這台電腦登入過（手動在終端機跑一次 `claude` 即可）。

## run_data.ps1 的事前準備

這支腳本不會自己下載資料，每期要手動放檔案：

1. 實價登錄每月 1、11、21 日更新。到內政部不動產交易實價查詢服務網的「資料開放」下載「本期下載」的全國 CSV 格式 zip。
2. 把 zip 放進 `C:\Real-estate\data\raw\` 底下依季分的資料夾，例如 `data\raw\2026Q4\`，不用解壓。腳本會檢查 `data\raw\` 和所有子資料夾裡的 zip，只處理還沒寫進 `district_metrics.csv` 的資料期間，所以一次放好幾期、或補舊的季資料都可以。檔名沿用 `lvr_landcsv.zip` 直接覆蓋也可以，腳本會發現 zip 比較新而重新解壓；但建議改成帶日期的名稱，例如 `lvr_landcsv_20261011.zip`，這樣每一期的原始檔都會留著，之後想重算也找得到。
3. 如果忘了放新檔，腳本會重算上一期的資料，但同一期的指標已經存在，不會重複寫入，所以不會弄亂資料。

處理邏輯在 `analysis\process_lvr.py`，需要 Python 和 pandas。目前使用的 Python 是 `C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe`；如果 log 出現找不到 python，把 `prompt_data.md` 裡的 `python` 換成這個完整路徑。

如果下載時間比排程晚，也可以放好檔案後自己在工作排程器按右鍵 →「執行」，不用等下一次排程。
