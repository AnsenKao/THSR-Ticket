import os
from typing import Mapping, Any

from playwright.sync_api import Browser, Error as PlaywrightError, sync_playwright

from thsr_ticket.configs.web.http_config import HTTPConfig
from thsr_ticket.remote.http_request import parse_security_img_url

# 清除 Playwright 自動化特徵，減少 Akamai Bot Manager 偵測
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['zh-TW', 'zh', 'en-US', 'en'] });
window.chrome = { runtime: {} };
const _origPermQuery = navigator.permissions.query.bind(navigator.permissions);
navigator.permissions.query = (p) =>
    p.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : _origPermQuery(p);
"""


class PlaywrightResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content


def _env_flag(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() not in ("0", "false", "no", "")


class PlaywrightHTTPRequest:
    """以瀏覽器發送 THSR 請求。

    Akamai Bot Manager 會擋掉 Playwright 內建的 Chromium headless（連線直接 hang），
    但放行系統安裝的 Chrome headless。因此預設用 channel="chrome" + headless，
    讓搶票迴圈可以在背景跑而不佔用桌面。
    可用環境變數覆寫：
      THSR_BROWSER_HEADLESS=0  改用有頭視窗
      THSR_BROWSER_CHANNEL=msedge  指定瀏覽器（預設依序試 chrome、msedge）
      THSR_BROWSER_CHANNEL=""  改用 Playwright 內建 Chromium（headless 會被擋）
    """

    def __init__(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser = self._launch_browser()
        self._context = self._browser.new_context(
            user_agent=HTTPConfig.HTTPHeader.USER_AGENT,
            locale="zh-TW",
            timezone_id="Asia/Taipei",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept-Language": HTTPConfig.HTTPHeader.ACCEPT_LANGUAGE,
                "Upgrade-Insecure-Requests": "1",
            },
        )
        self._context.add_init_script(_STEALTH_SCRIPT)
        self._page = self._context.new_page()

    def request_booking_page(self) -> PlaywrightResponse:
        self._page.goto(HTTPConfig.BOOKING_PAGE_URL, wait_until="domcontentloaded", timeout=HTTPConfig.HTTP_TIMEOUT * 1000)
        # 若出現個人資料使用說明同意視窗，點擊「我同意」關閉它
        consent_btn = self._page.locator("button:has-text('我同意')")
        if consent_btn.is_visible():
            consent_btn.click()
        return PlaywrightResponse(self._page.content().encode("utf-8"))

    def request_security_code_img(self, book_page: bytes) -> PlaywrightResponse:
        # 明確發一次 GET 請求取得驗證碼圖片，確保伺服器 session 對應的是這次的驗證碼
        img_url = parse_security_img_url(book_page)
        resp = self._page.request.get(img_url, timeout=HTTPConfig.HTTP_TIMEOUT * 1000)
        return PlaywrightResponse(resp.body())

    def submit_booking_form(self, params: Mapping[str, Any]) -> PlaywrightResponse:
        cookies = self._context.cookies()
        jsessionid = next(
            (c["value"] for c in cookies if c["name"] == "JSESSIONID"), ""
        )
        url = HTTPConfig.SUBMIT_FORM_URL.format(jsessionid)
        resp = self._page.request.post(
            url,
            params={k: str(v) for k, v in params.items() if v is not None},
            timeout=HTTPConfig.HTTP_TIMEOUT * 1000,
        )
        return PlaywrightResponse(resp.body())

    def submit_train(self, params: Mapping[str, Any]) -> PlaywrightResponse:
        resp = self._page.request.post(
            HTTPConfig.CONFIRM_TRAIN_URL,
            params={k: str(v) for k, v in params.items() if v is not None},
            timeout=HTTPConfig.HTTP_TIMEOUT * 1000,
        )
        return PlaywrightResponse(resp.body())

    def submit_ticket(self, params: Mapping[str, Any]) -> PlaywrightResponse:
        resp = self._page.request.post(
            HTTPConfig.CONFIRM_TICKET_URL,
            params={k: str(v) for k, v in params.items() if v is not None},
            timeout=HTTPConfig.HTTP_TIMEOUT * 1000,
        )
        return PlaywrightResponse(resp.body())

    def _launch_browser(self) -> Browser:
        headless = _env_flag("THSR_BROWSER_HEADLESS", True)
        env_channel = os.environ.get("THSR_BROWSER_CHANNEL")
        if env_channel is not None:
            channels = [env_channel.strip()]
        else:
            # Windows 不一定裝 Chrome，但一定有 Edge，兩者都是正式版 Chromium binary
            channels = ["chrome", "msedge"]

        for channel in channels:
            try:
                return self._playwright.chromium.launch(
                    headless=headless, channel=channel or None
                )
            except PlaywrightError:
                continue

        # 找不到任何系統瀏覽器時退回內建 Chromium，此時只有有頭模式不會被擋
        return self._playwright.chromium.launch(headless=False)

    def close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._playwright.stop()
