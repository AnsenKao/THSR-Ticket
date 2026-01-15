import json
from typing import Tuple

from bs4 import BeautifulSoup
from requests.models import Response
from thsr_ticket.configs.web.param_schema import ConfirmTicketModel

from thsr_ticket.model.db import Record
from thsr_ticket.remote.http_request import HTTPRequest


class ConfirmTicketFlow:
    def __init__(self, client: HTTPRequest, train_resp: Response, record: Record = None):
        self.client = client
        self.train_resp = train_resp
        self.record = record

    def run(self) -> Tuple[Response]:
        page = BeautifulSoup(self.train_resp.content, features='html.parser')
        ticket_model = ConfirmTicketModel(
            personal_id=self.set_personal_id(),
            phone_num=self.set_phone_num(),
            member_radio=_parse_member_radio(page),
        )

        json_params = ticket_model.json(by_alias=True)
        dict_params = json.loads(json_params)
        
        # Auto-fill passenger IDs for discounted tickets (Elder/Disabled) using the main ID
        # Finding all inputs for passenger IDs
        # Format usually: TicketPassengerInfoInputPanel:passengerDataView:X:passengerDataView2:passengerDataIdNumber
        passenger_id_inputs = page.find_all('input', attrs={'name': lambda x: x and 'passengerDataIdNumber' in x})
        
        if passenger_id_inputs and self.record and self.record.personal_id:
             for inp in passenger_id_inputs:
                 # Check if it's visible or likely required? 
                 # Usually hidden inputs are for non-required or pre-filled?
                 # Actually, for Adults, the input might be hidden or not present.
                 # For Elder, it is present.
                 # We just fill all we find.
                 key = inp.attrs.get('name')
                 if key:
                     dict_params[key] = self.record.personal_id

        resp = self.client.submit_ticket(dict_params)
        return resp, ticket_model

    def set_personal_id(self) -> str:
        if self.record and (personal_id := self.record.personal_id):
            return personal_id
        return input('輸入身分證字號：\n')

    def set_phone_num(self) -> str:
        if self.record and (phone_num := self.record.phone):
            return phone_num
        phone_num = input('輸入手機號碼（預設：""）：\n')
        return phone_num or ""


def _parse_member_radio(page: BeautifulSoup) -> str:
    candidates = page.find_all(
        'input',
        attrs={
            'name': 'TicketMemberSystemInputPanel:TakerMemberSystemDataView:memberSystemRadioGroup'
        },
    )
    tag = next((cand for cand in candidates if 'checked' in cand.attrs))
    return tag.attrs['value']
