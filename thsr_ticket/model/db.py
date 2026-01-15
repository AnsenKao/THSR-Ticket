import os
from typing import Mapping, List, Iterable, Any, NamedTuple

from tinydb import TinyDB, Query
from tinydb.database import Document

from thsr_ticket import MODULE_PATH
from thsr_ticket.configs.web.param_schema import ConfirmTicketModel
from thsr_ticket.view.history_view import history_info


class Record(NamedTuple):
    personal_id: str = None
    phone: str = None
    start_station: int = None
    dest_station: int = None
    outbound_time: str = None
    adult_num: str = None
    outbound_date: str = None
    outbound_delay_time: str = None
    child_ticket_num: str = None
    disabled_ticket_num: str = None
    elder_ticket_num: str = None
    college_ticket_num: str = None


class ParamDB:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(MODULE_PATH, ".db", "history.json")
        self.db_path = db_path
        db_dir = db_path[:db_path.rfind("/")]
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def save(self, record: Record, ticket: ConfirmTicketModel) -> None:
        data = Record(
            ticket.personal_id,
            ticket.phone_num,
            record.start_station,
            record.dest_station,
            record.outbound_time,
            record.adult_num,
            record.outbound_date,
            record.outbound_delay_time,
            record.child_ticket_num,
            record.disabled_ticket_num,
            record.elder_ticket_num,
            record.college_ticket_num
        )._asdict()  # type: ignore
        with TinyDB(self.db_path, sort_keys=True, indent=4) as db:
            hist = db.search(Query().personal_id == ticket.personal_id)
            if self._compare_hist(data, hist) is None:
                db.insert(data)

    def get_history(self) -> List[Record]:
        with TinyDB(self.db_path) as db:
            dicts = db.all()
        return [Record(**d) for d in dicts]   # type: ignore

    def _compare_hist(self, data: Mapping[str, Any], hist: Iterable[Document]) -> int:
        for idx, h in enumerate(hist):
            # Check if all keys in data match the record in history
            # If a key is missing in history, it doesn't match
            match = True
            for k, v in data.items():
                if k not in h or h[k] != v:
                    match = False
                    break
            if match:
                return idx
        return None

    def get_history_record(self) -> Record:
        """獲取用戶選擇的歷史紀錄
        
        Returns:
            Record: 選擇的歷史紀錄，如果沒有選擇則返回 None
        """
        hist = self.get_history()
        if not hist:
            return None
            
        h_idx = history_info(hist)
        if h_idx is not None:
            return hist[h_idx]
        return None
