# 安全設計與範圍

Django DB sessions、密碼雜湊與 CSRF，Axes 登入限速；Waitress 僅綁 127.0.0.1，不信任轉送 header。沒有 Django Admin、上傳、文件修改、命令執行 API 或遠端管理 API。資料夾管理與暫停是本機命令列操作。

所有 /api 接口先驗證有效帳號、裝置、全域撤銷世代、暫停與最長登入時間，下載、預覽、搜尋再驗證 root 存在及範圍。文件路徑和搜尋條件放 POST body；密碼與 session 不放 URL。登入後 cookie 為 HttpOnly、SameSite=Strict；CSRF token 是標準表單保護，並非認證憑證。HTML、SVG、Office 只能 attachment/octet-stream，點陣圖／PDF／文字預覽限定副檔名且上限 20 MiB，內容以 nosniff 與 CSP sandbox 防護。這不是文件清毒器，下載後須用受維護的 App 開啟；PDF.js 和作業系統本身仍需更新。

## 檔案邊界

不做字串 prefix 授權、不自行 URL decode 已解析的路徑；拒絕絕對路徑、反斜線、冒號／ADS、空元件、..、保留裝置名稱及尾端點／空白。中文與 Unicode 交由 OS 處理，不將不同 Unicode 名稱錯誤合併。

POSIX 使用 root 的 device/inode 身份、openat(dir_fd)、O_NOFOLLOW、O_DIRECTORY，逐層固定目錄，最終僅讀 regular file。Windows 使用寬字元 CreateFileW、OPEN_REPARSE_POINT、逐層開啟磁碟或 UNC share 至文件的所有祖先；拒絕所有 reparse point，handle 不分享寫入或刪除，阻止檢查後修改 reparse／更名；root 比對 volume/file identity。檔案用同一 handle 轉 Python fd 後串流，不在驗證後重新按名稱開檔。目錄列舉期間持有祖先 handle。檔案被編輯器、同步工具或其他程序寫入時可能無法取得 Windows handle；正常回報錯誤，請稍後重試。

這些檢查在應用內限制白名單；OS 同時以目前普通使用者權限執行每次檔案開啟。不聲稱 OS 帳戶已被沙箱限制至白名單；應用的主機帳戶不可給予額外機密權限，請 IT 以最小 NTFS／SMB read ACL 配置專用讀取資料夾。不能防禦同帳戶惡意程序、管理員、核心或惡意檔案系統。硬連結是同一檔案的另一名稱，v1 不拒絕；白名單內的硬連結視作本機管理者批准內容，IT 應控制允許資料夾的寫入權。拒絕符號連結與 junction。

搜尋逐目錄讀取，不建立全文索引；每次最多掃描 20,000 項、保留 2,000 筆結果、執行 15 秒，結果每頁 50。4 個背景搜尋、最多 32 個快取，每裝置一個搜尋；快取 5 分鐘，重啟失效。取消每 32 項／目錄檢查，OS 對離線 UNC 的阻塞呼叫無法強制中斷，可能需等待 Windows 網絡逾時；可停止程序。排序僅針對已掃描的結果，達上限需縮小範圍。

串流使用固定大小區塊，逐塊重查裝置、世代、root、時限；正在傳送的區塊及已下載文件無法撤回。v1 沒有 HTTP Range／續傳，PDF 使用內附 PDF.js 渲染至 canvas，關閉 eval／XFA，無文件 action／表單／連結執行；圖片顯示依瀏覽器能力，Safari 實機仍待驗證。文字／圖片預覽採隔離 iframe，PDF 採 canvas，無法可靠預覽時請下載。沒有縮圖接口。

## 日誌

`.local/audit.log` 記錄時間、登入成功／失敗、拒絕、撤銷、預覽、下載及檔案錯誤，不記內容、搜尋詞、完整路徑、密碼或 session key。日誌最多 2 MB × 4 檔，非不可竄改集中式稽核。資料庫含 Axes 的限速 metadata。保留與集中稽核由 IT 決定。入口亦不可記錄 POST body、cookie、authorization 或敏感查詢。

目前 localhost HTTP 的 cookie 不設 Secure；遠端部署前必須完成 REMOTE.md 的 HTTPS／MFA／cookie 及代理信任設定與實測。不能直接把此端口公開。
