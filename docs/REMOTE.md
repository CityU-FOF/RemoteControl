# 遠端部署：尚未實施

目前沒有 VPN、公開 tunnel、防火牆規則、router port、RDP 或系統服務。iPhone 不能直接連公司電腦的 127.0.0.1。未做跨網絡測試，不宣稱居家可用。MFA **尚未整合至本機程式**，是啟用遠端存取前的必要外部門檻。

建議 IT 以機構已有受控入口／身份感知代理配合私人網絡，採機構 IdP MFA、HTTPS 與裝置／使用者存取政策；保留本程式自己的 session 驗證。只有 VPN 的 MFA 並不自動保護每次網頁使用，需 IT 核實會話政策。不要使用未獲批准私人 VPN 或私人雲端。

需要 IT 提供：

1. 批准的平台、文件分類與可下載政策、iPhone 是否需 MDM，以及允許使用者／裝置。
2. IdP／SSO／MFA 強制條件、重新驗證週期、撤銷及離職停權流程。
3. 私人 DNS／HTTPS hostname、有效憑證、入口與公司 Windows 的連通方式；入口應只能經受控渠道到本機 Agent。
4. 是否允許使用者程序運行，Windows 登出／睡眠時的可用性要求；若需持續運行，要另行評估機構管理的服務與帳戶，不自動安裝。
5. 指定資料夾及 NTFS／SMB 最小讀取 ACL、UNC 認證方式，是否有 junction／OneDrive placeholders／DLP 限制。
6. 稽核保留、下載大小／逾時、incident response 與資料外洩處理。

批准後的具體變更需另行審查：設定精確 ALLOWED_HOSTS、CSRF_TRUSTED_ORIGINS、HTTPS Secure cookies；只信任已知代理的 scheme／host header，禁止其他來源偽造；代理剝除來客 forwarded headers。維持後端 localhost 並由 IT 管理的本機入口轉送，或另行核准最小網絡配置。不以 `*` 主機或廣泛 trusted origins 繞過保護。反向代理禁止快取及敏感 access log；配置大型下載及取消／斷線資源釋放。

完成入口設定後仍需實測：iPhone Safari MFA、失效／撤銷、登出、中文附件名稱、PDF／圖片預覽、大檔串流、受管 App 開啟、UNC 斷線、未授權網段／非 MFA 存取確實被拒絕，以及 Windows 鎖屏／登出／睡眠行為。這些未完成前不要投入公司遠端使用。
