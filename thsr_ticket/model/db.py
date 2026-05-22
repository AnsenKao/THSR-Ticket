import os
import threading
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
    preferred_trains: Iterable[str] = None


class ParamDB:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(MODULE_PATH, ".db", "history.json")
        self.db_path = db_path
        db_dir = db_path[:db_path.rfind("/")]
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        self.lock = threading.Lock()

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
            record.college_ticket_num,
            record.preferred_trains
        )._asdict()  # type: ignore
        
        with self.lock:
            with TinyDB(self.db_path, sort_keys=True, indent=4) as db:
                hist = db.search(Query().personal_id == ticket.personal_id)
                if self._compare_hist(data, hist) is None:
                    db.insert(data)

    def get_history(self) -> List[Record]:
        with self.lock:
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

    @staticmethod
    def _normalize_delay(val: str) -> str:
        """'23' -> '2300', '1800' -> '1800' (keep HHMM format)."""
        if not val:
            return "2300"
        s = str(val)
        return s + "00" if len(s) <= 2 else s

    def save_record(self, record) -> None:
        """Save booking profile on submit (no date, dedup by identity + route + time)."""
        data = {
            'personal_id': getattr(record, 'personal_id', None),
            'phone': getattr(record, 'phone', None),
            'start_station': getattr(record, 'start_station', None),
            'dest_station': getattr(record, 'dest_station', None),
            'outbound_time': getattr(record, 'outbound_time', None),
            'adult_num': getattr(record, 'adult_num', None),
            'outbound_delay_time': self._normalize_delay(getattr(record, 'outbound_delay_time', None)),
            'child_ticket_num': getattr(record, 'child_ticket_num', None),
            'disabled_ticket_num': getattr(record, 'disabled_ticket_num', None),
            'elder_ticket_num': getattr(record, 'elder_ticket_num', None),
            'college_ticket_num': getattr(record, 'college_ticket_num', None),
            'preferred_trains': list(record.preferred_trains) if getattr(record, 'preferred_trains', None) else None,
        }
        key = (
            (Query().personal_id == data['personal_id']) &
            (Query().start_station == data['start_station']) &
            (Query().dest_station == data['dest_station']) &
            (Query().outbound_time == data['outbound_time']) &
            (Query().adult_num == data['adult_num'])
        )
        with self.lock:
            with TinyDB(self.db_path, sort_keys=True, indent=4) as db:
                if db.contains(key):
                    db.update(data, key)
                else:
                    db.insert(data)

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
