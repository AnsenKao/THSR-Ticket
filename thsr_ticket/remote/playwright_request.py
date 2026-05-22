from typing import Mapping, Any

from playwright.sync_api import sync_playwright

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


class PlaywrightHTTPRequest:
    def __init__(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=False)
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

    def close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._playwright.stop()
