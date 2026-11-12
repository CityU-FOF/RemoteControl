# 依賴選用及授權

2026-11-12 從官方 PyPI 以 TLS 安裝並鎖定；沒有 fork／拼接既有遠端控制專案。選擇維護中的成熟框架，避免建立自己的認證、密碼雜湊或加密協議。未使用 RDP、VPN、tunnel 套件。

| 套件（requirements.lock） | 授權 | 選用理由與限制 |
|---|---|---|
| Django 5.2.19 | BSD-3-Clause | 5.2 LTS 分支；內建認證、DB session、CSRF、ORM、migration。預設開發伺服器不作部署用途。 |
| django-axes 8.3.1 | MIT | 維護中的 Django 登入防暴力套件，帳號／IP 限速；不是 MFA，也不是網絡防火牆。 |
| Waitress 3.0.2 | ZPL-2.1 | 維護中的跨平台 WSGI server，支援 Windows 普通使用者；此版本只監聽 loopback，沒有 TLS 終止。 |
| asgiref 3.13.0 | BSD-3-Clause | Django 相依。 |
| sqlparse 0.6.1 | BSD-3-Clause | Django 相依。 |

官方維護／授權依據：安裝版本的 PyPI metadata、隨包 license；上游分別為 https://www.djangoproject.com/ 、https://github.com/jazzband/django-axes 、https://github.com/Pylons/waitress 。本次取得的版本可安裝且整合測試通過；這不代表永久沒有漏洞，部署前須重新檢查安全公告與支援期限，升級後重跑測試，不自動漂移鎖定版本。

開發鎖檔額外包含 Playwright 1.65.1（Apache-2.0）及 greenlet 3.5.6（MIT／PSF-2.0），僅作瀏覽器測試；Chromium 應由機構批准渠道提供。PDF 預覽另外附帶 Mozilla PDF.js，詳見下段。


## PDF.js vendor

PDF.js `pdfjs-dist` 6.5.438，Apache-2.0，來自 Mozilla 維護的 https://github.com/mozilla/pdf.js 。官方 npm registry 的固定版本經 `npm pack pdfjs-dist@6.5.438` 取得，保留 Apache LICENSE、字型及 cmap 各自的授權檔。`pdfjs-vendor.lock.json` 記錄 npm tarball integrity 與每個附帶檔案的 SHA-256；`python tools/verify_vendor.py` 驗證。瀏覽器使用 legacy build、獨立 worker、內附 cmap／字型／WASM／色彩檔；不依賴 CDN，使用者無需 Node 或 npm。升級 vendor 是獨立維護操作，必須重新核對官方來源、授權、雜湊與瀏覽器測試，不能只更改雜湊掩蓋損壞。

只呼叫 PDF.js 頁面 canvas renderer，不採用可執行 action、連結、表單或 JavaScript 的 viewer；關閉 eval、XFA 與 FontFace。每次一頁、每頁最多 400 萬像素、上限 200 頁。複雜 PDF、特殊字型或瀏覽器相容性仍可能失敗，提供原檔下載。隨檔字型授權維持原文件，未改寫。
