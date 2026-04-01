from typing import Mapping, Any

from playwright.sync_api import sync_playwright

from thsr_ticket.configs.web.http_config import HTTPConfig
from thsr_ticket.remote.http_request import parse_security_img_url


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
            extra_http_headers={
                "Accept-Language": HTTPConfig.HTTPHeader.ACCEPT_LANGUAGE,
            },
        )
        self._page = self._context.new_page()

    def request_booking_page(self) -> PlaywrightResponse:
        self._page.goto(HTTPConfig.BOOKING_PAGE_URL, wait_until="domcontentloaded", timeout=HTTPConfig.HTTP_TIMEOUT * 1000)
        return PlaywrightResponse(self._page.content().encode("utf-8"))

    def request_security_code_img(self, book_page: bytes) -> PlaywrightResponse:
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
