"""
DB migration script — run once per machine.

Changes:
  - Remove outbound_date field from all records
  - Normalize outbound_delay_time to HHMM format (e.g. "23" -> "2300")
  - Deduplicate by (personal_id, start_station, dest_station, outbound_time, adult_num)
    keeping the latest record when duplicates exist

Usage:
    uv run python scripts/migrate_db.py
    python scripts/migrate_db.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tinydb import TinyDB

from thsr_ticket import MODULE_PATH


def normalize_delay(val) -> str:
    if not val:
        return "2300"
    s = str(val)
    return s + "00" if len(s) <= 2 else s


def main():
    db_path = os.path.join(MODULE_PATH, ".db", "history.json")
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}, nothing to migrate.")
        return

    with TinyDB(db_path, sort_keys=True, indent=4) as db:
        all_docs = db.all()
        before = len(all_docs)
        print(f"Records before: {before}")

        # Deduplicate: keep latest doc_id per key
        seen: dict = {}
        for doc in sorted(all_docs, key=lambda d: d.doc_id):
            key = (
                doc.get("personal_id"),
                doc.get("start_station"),
                doc.get("dest_station"),
                doc.get("outbound_time"),
                doc.get("adult_num"),
            )
            seen[key] = doc.doc_id

        keep_ids = set(seen.values())
        remove_ids = [d.doc_id for d in all_docs if d.doc_id not in keep_ids]
        if remove_ids:
            db.remove(doc_ids=remove_ids)
            print(f"Removed {len(remove_ids)} duplicates (doc_ids: {remove_ids})")

        # Clean each remaining record
        for doc in db.all():
            cleaned = {k: v for k, v in doc.items() if k != "outbound_date"}
            cleaned["outbound_delay_time"] = normalize_delay(doc.get("outbound_delay_time"))
            db.update(cleaned, doc_ids=[doc.doc_id])

        after = len(db.all())
        print(f"Records after:  {after}")
        print("Migration complete.")


if __name__ == "__main__":
    main()
