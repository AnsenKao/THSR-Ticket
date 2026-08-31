import os
import threading
from datetime import datetime
from typing import Mapping, List, Iterable, Any, NamedTuple

from tinydb import TinyDB, Query

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
    updated_at: str = None


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
        """Save booking profile after a successful booking."""
        data = self._build_data(
            record, personal_id=ticket.personal_id, phone=ticket.phone_num
        )
        self._upsert(data)

    def get_history(self) -> List[Record]:
        with self.lock:
            with TinyDB(self.db_path) as db:
                docs = db.all()
        # Oldest first; callers (and the web UI) reverse this to show newest first.
        # Records without updated_at predate the timestamp and fall back to doc_id.
        docs = sorted(docs, key=lambda d: (d.get("updated_at") or "", d.doc_id))
        return [
            Record(**{k: v for k, v in d.items() if k in Record._fields})  # type: ignore
            for d in docs
        ]

    @staticmethod
    def _normalize_delay(val: str) -> str:
        """'23' -> '2300', '1800' -> '1800' (keep HHMM format)."""
        if not val:
            return "2300"
        s = str(val)
        return s + "00" if len(s) <= 2 else s

    def save_record(self, record) -> None:
        """Save booking profile on submit (dedup by identity + route + time)."""
        self._upsert(self._build_data(record))

    def _build_data(
        self, record, personal_id: str = None, phone: str = None
    ) -> Mapping[str, Any]:
        data = {k: getattr(record, k, None) for k in Record._fields}
        if personal_id:
            data["personal_id"] = personal_id
        if phone:
            data["phone"] = phone
        data["outbound_delay_time"] = self._normalize_delay(
            data["outbound_delay_time"]
        )
        trains = data["preferred_trains"]
        data["preferred_trains"] = (
            [str(t).strip() for t in trains if str(t).strip()] if trains else None
        )
        data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        return data

    def _upsert(self, data: Mapping[str, Any]) -> None:
        q = Query()
        key = (
            (q.personal_id == data["personal_id"]) &
            (q.start_station == data["start_station"]) &
            (q.dest_station == data["dest_station"]) &
            (q.outbound_time == data["outbound_time"]) &
            (q.adult_num == data["adult_num"])
        )
        with self.lock:
            with TinyDB(self.db_path, sort_keys=True, indent=4) as db:
                matches = db.search(key)
                if not matches:
                    db.insert(data)
                    return
                # Keep the first match, refresh it, and drop the duplicates that
                # earlier versions left behind (update() hit every match).
                db.update(data, doc_ids=[matches[0].doc_id])
                extra = [d.doc_id for d in matches[1:]]
                if extra:
                    db.remove(doc_ids=extra)

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
