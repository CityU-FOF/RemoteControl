# 遠端文件助手 v1

供 Windows 11 普通帳戶啟動的唯讀文件網頁，以 iPhone 尺寸設計。**目前交付 localhost 版本，未完成 Windows 11／iPhone Safari 實機或跨網絡驗證，不代表已可從家中連接公司。**

## Windows 本機開始

需要機構批准的 Python 3.12（使用者安裝即可）、可寫的私人 NTFS 專案目錄，以及套件下載權限。不需要管理員、Node、AI 或付費 API。請使用普通命令提示字元，勿以管理員執行。

1. 將專案放在只有自己可存取的目錄；避免共用磁碟、同步資料夾或其他使用者可寫的目錄。
2. 執行 `setup.cmd`，建立 `.venv`、安裝鎖定依賴並建立資料庫。再次執行可重用。
3. 設定帳號及**明確選定**的資料夾（下列路徑只是例子）：

```bat
.venv\Scripts\python.exe manage.py local user reader
.venv\Scripts\python.exe manage.py local add "C:\Users\你的帳號\Documents\可分享文件" --label "工作文件"
.venv\Scripts\python.exe manage.py local list
```

密碼在提示中輸入，不放在參數、腳本或日誌；至少 12 字元。再次執行 `local user reader` 可更換密碼並撤銷該帳號裝置。所有帳號共用同一組白名單；v1 不提供每人不同的資料夾權限。

4. 執行 `start.cmd`，在**同一台 Windows 電腦**的瀏覽器開啟 `http://127.0.0.1:8765`。沒有配置公開端口或對外預覽連結。
5. 用登入帳號瀏覽、搜尋、預覽或下載。Office 等格式僅列出檔名、資料夾、日期、大小及下載。日期篩選以 UTC 日界為準，畫面時間以裝置時區顯示。
6. 在啟動視窗按 Ctrl+C 停止。v1 不安裝服務、不設開機啟動。

## 本機管理與緊急停止

以下命令只在公司電腦本機命令列執行，手機沒有對應管理 API。`ID` 由 list 或 devices 查得。

```bat
.venv\Scripts\python.exe manage.py local remove ID
.venv\Scripts\python.exe manage.py local pause
.venv\Scripts\python.exe manage.py local resume
.venv\Scripts\python.exe manage.py local devices
.venv\Scripts\python.exe manage.py local revoke ID
.venv\Scripts\python.exe manage.py local revoke-all
```

`pause` 會暫停所有文件 API 並撤銷所有登入；`resume` 後需重新登入。移除資料夾後，舊搜尋結果及新文件請求會被拒絕。進行中的串流在下一個 64 KiB 區塊檢查中止；已傳給瀏覽器的資料無法收回。手機亦可撤銷自己帳號的登入裝置，或登出。

拒絕設定整個磁碟、整個使用者目錄及使用者預設 Desktop。重新導向的桌面請自行選定明確子資料夾，不分享整個桌面。拒絕重疊的白名單。資料夾更名／更換後需移除再新增。UNC 使用現有 Windows 身份及分享／NTFS 權限，例如 `\\server\share\team\approved`；不儲存 SMB 帳密，不提升權限、不修改文件 ACL。斷線、鎖定、權限不足、OneDrive reparse 檔案會正常拒絕，不能保證雲端 placeholder 預覽。

**本機管理的信任邊界是 Windows 帳戶與 NTFS ACL。** 同帳戶執行的其他程式可讀取 `.local` 並管理本程式；不要在不受信任或共用帳戶執行。`.local` 含密碼雜湊、session、隨機金鑰及稽核日誌，必須維持私人 ACL；備份也要保護。不可將它提交 Git 或分享。程式不會修改原文件權限。

登入閒置逾時 30 分鐘、最長 8 小時；每次新登入建立裝置編號。5 次失敗觸發帳號或來源 IP 的 15 分鐘限速。管理者可在本機檢查稽核，必要時用 Django Axes 的 `manage.py axes_reset` 清除限速，勿將它暴露成網頁。

## 普通帳戶執行狀態

- 鎖屏：通常仍執行，受公司政策、網絡與電源管理影響，無需解鎖維持。
- 登出 Windows：使用者程式停止，不提供文件。
- 休眠／睡眠：無法連接，恢復後檢查服務及 session。
- 重開機：需使用者正常登入並重新執行 `start.cmd`。不自動登入、不停用 UAC。
- 停止後移除：確認沒有程序執行，刪除專案及其 `.venv`、`.local` 即可；不會刪除已授權資料夾內文件。已下載的副本需按公司政策另行處理。

## 開發及驗證

Linux/macOS 本機開發（正式目標仍是 Windows）：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py local user reader
.venv/bin/python manage.py local add /absolute/approved/folder --label 文件
.venv/bin/python serve.py
.venv/bin/python manage.py test tests
```

Windows 測試：`.venv\Scripts\python.exe manage.py test tests`。測試使用臨時文件，不碰授權文件。資料庫 migration 不可省略。

瀏覽器模擬：另安裝 `requirements-dev.lock`，用已安裝的 Chromium 設定 `CHROMIUM_PATH`，執行 `python tests/browser_smoke.py`。Linux 預設 `/usr/bin/chromium`；腳本建立隔離臨時帳號、文件與服務，完成後清除並停止服務。它使用 8765，請先停止自己的服務。`RFA_STATE` 可指定獨立的私人狀態目錄，不可指向別人的狀態。

詳見 [安全設計及限制](docs/SECURITY.md)、[IT 遠端部署條件](docs/REMOTE.md)、[實際測試結果](docs/TESTING.md)、[依賴與授權](docs/DEPENDENCIES.md)。
