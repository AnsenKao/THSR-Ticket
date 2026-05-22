from requests.models import Response

from thsr_ticket.controller.confirm_train_flow import ConfirmTrainFlow
from thsr_ticket.controller.confirm_ticket_flow import ConfirmTicketFlow
from thsr_ticket.controller.first_page_flow import FirstPageFlow
from thsr_ticket.view_model.error_feedback import ErrorFeedback
from thsr_ticket.view_model.booking_result import BookingResult
from thsr_ticket.view.web.show_error_msg import ShowErrorMsg
from thsr_ticket.view.web.show_booking_result import ShowBookingResult
from thsr_ticket.model.db import ParamDB
from thsr_ticket.remote.http_request import HTTPRequest



from thsr_ticket.ml.model import CaptchaSolver

class BookingFlow:
    def __init__(self, record=None, captcha_solver: CaptchaSolver = None) -> None:
        self.client = HTTPRequest()
        self.db = ParamDB()
        self.error_feedback = ErrorFeedback()
        self.show_error_msg = ShowErrorMsg()
        self.record = record
        self.captcha_solver = captcha_solver

    _CAPTCHA_ERROR_KEYWORDS = ("驗證碼", "security code", "captcha", "verification code")

    def run(self) -> Response:
        # First page. Booking options — retry same session only for captcha errors
        CAPTCHA_MAX_RETRIES = 3
        for attempt in range(CAPTCHA_MAX_RETRIES):
            book_resp, book_model, updated_record = FirstPageFlow(client=self.client, record=self.record, captcha_solver=self.captcha_solver).run()
            self.record = updated_record
            errors = ErrorFeedback().parse(book_resp.content)
            if not errors:
                break
            self.show_error_msg.show(errors)
            is_captcha = any(
                any(k in e.msg.lower() for k in self._CAPTCHA_ERROR_KEYWORDS)
                for e in errors
            )
            if not is_captcha or attempt == CAPTCHA_MAX_RETRIES - 1:
                return book_resp

        # Second page. Train confirmation
        train_resp, train_model = ConfirmTrainFlow(self.client, book_resp, record=self.record).run()
        if self.show_error(train_resp.content):
            return train_resp

        # Final page. Ticket confirmation
        ticket_resp, ticket_model = ConfirmTicketFlow(self.client, train_resp, self.record).run()
        if self.show_error(ticket_resp.content):
            return ticket_resp

        # Result page.
        result_model = BookingResult().parse(ticket_resp.content)
        book = ShowBookingResult()
        book.show(result_model)
        print("\n請使用官方提供的管道完成後續付款以及取票!!")
       
        # Save booking history
        self.db.save(self.record, ticket_model)
       
        status = 'Finish'
        return status

    def show_error(self, html: bytes) -> bool:
        errors = self.error_feedback.parse(html)
        if len(errors) == 0:
            return False

        self.show_error_msg.show(errors)
        return True
