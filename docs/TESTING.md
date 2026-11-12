# 實際驗證結果

日期：2026-11-12。環境：Linux、普通使用者、Python 3.12.14、Chromium（Playwright 1.65.1 控制）、鎖檔中的依賴。沒有公司文件／憑證；測試全部使用臨時合成資料。未發佈、未推送、未做跨網絡測試。

## 已執行

- `python manage.py test tests`：**24 項，23 通過、1 跳過、0 失敗**。跳過的是 Windows junction 測試，Linux 無法驗證 Windows 分支。
- 檔名：中文、空格、`# & [ ] + %`、子資料夾同名檔案；部分字詞、大小排序、類型及日期篩選、50 筆分頁、搜尋上限。
- 認證：未登入／撤銷後所有文件 API 拒絕；登入限速實際返回 429；CSRF、HTTP 方法限制、登出、閒置過期、8 小時上限、暫停／恢復與撤銷全部登入。
- 授權：移除資料夾後搜尋、結果、預覽、下載失效；移除 root 或撤銷 session 會中止後續串流區塊；搜尋中移除資料夾不回傳資料。
- 路徑：`..`、多層 URL 編碼字面值、絕對路徑、反斜線、ADS、尾點、保留名稱、相似 root 名稱、符號連結文件及目錄逃逸、root 被替換。
- 故障：檔案消失、離線 root、實際 POSIX 權限拒絕及 mock PermissionError、25 MiB 稀疏檔串流（首塊及撤銷中斷）、背景搜尋取消和其他 session 不可讀取 job。
- 預覽：PDF／PNG MIME 與資料流、純文字 nosniff／sandbox、HTML／SVG／Office attachment、過大檔案拒絕預覽。
- `python tests/browser_smoke.py`：啟動真實 Waitress，使用真實 Chromium；**通過**登入 → 搜尋 → 文字 iframe → 中文附件下載並核對 bytes → PNG native viewer → 有效 PDF 經 PDF.js canvas 實際繪製非透明文字像素 → Office 基本資料及無預覽按鈕 → 裝置列表 → 登出。沒有未處理 JS 錯誤。合成 PDF 只一頁，不代表複雜企業文件相容性已全測。
- 手機尺寸：390 × 844、觸控及 mobile 模擬，另檢查 375、430、768 寬度無橫向溢出；**不是 iPhone Safari／WebKit 實機驗證**。
- migration 首次建立及再次執行成功；Django check、migration drift、pip check、JavaScript syntax、205 個 PDF.js vendor 雜湊與自有程式碼的 Git whitespace 檢查通過（vendor 保留上游原始空白及位元組）。

瀏覽器驗證發現並修正了 no-referrer 導致表單 Origin=null 的 CSRF 問題，改成 same-origin；原生 PDF 在 sandbox 被阻擋，改用本機 PDF.js canvas；關閉 PDF 與新搜尋同時操作的清理競態已修正並重跑流程。對預覽中的文件，介面提供「下載目前文件」，亦可先關閉預覽再下載列表項目。

## 必須補做的驗證與限制

- Windows 11 普通帳戶：執行 setup.cmd、登入、完整測試；特別驗證 CreateFileW 的 ancestor pinning、NTFS 大小寫、junction、UNC／SMB、檔案佔用及 OneDrive reparse 行為。本次僅實作 Windows 分支及條件測試，**沒有 Windows 執行結果**。
- Windows 專用 junction 測試使用普通帳戶 `cmd /c mklink /J` 建立測試用臨時 junction，不要求開啟 symlink privilege；一般 symlink 測試在無建立權限時會另行跳過。這是測試工具，應用本身沒有執行命令接口。
- iPhone Safari：實際觸控、PDF 字型／多頁、圖片格式、中文附件名稱、大檔下載、儲存到「檔案」及交由受管 App 開啟。
- 未完整下載數 GB 檔、未做大量並行壓力／長時間 soak；25 MiB 測試驗證串流及中斷，沒有把整檔放記憶體。沒有 Range／續傳。
- 取消在 Python 掃描迴圈生效；卡在 OS 的 UNC I/O 仍需等系統逾時。部分檔案／資料夾因權限、reparse 或讀寫佔用不提供預覽。
- 沒有安全清毒、DLP、不可竄改集中稽核或外部滲透審計。依賴安全更新與公司 endpoint 控制仍是必要條件。
- IT 批准的私人網絡／受控入口、HTTPS 及強制 MFA 尚未配置；未驗證家庭網絡到公司，**不可聲稱已可遠端使用**。
