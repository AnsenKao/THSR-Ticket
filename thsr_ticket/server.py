import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
import sys
import os

# Ensure we can import from thsr_ticket
sys.path.append(os.getcwd())

from thsr_ticket.model.db import ParamDB, Record
from thsr_ticket.controller.booking_flow import BookingFlow
from thsr_ticket.controller.confirm_train_flow import ConfirmTrainFlow
from thsr_ticket.controller.confirm_ticket_flow import ConfirmTicketFlow
from thsr_ticket.view_model.booking_result import BookingResult
from thsr_ticket.ml.model import CaptchaSolver
from thsr_ticket.remote.http_request import HTTPRequest
from thsr_ticket.controller.non_interactive_flows import NonInteractiveFirstPageFlow
from thsr_ticket.view_model.error_feedback import ErrorFeedback

# Initialize reusable components
app = FastAPI()



# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

db = ParamDB()
captcha_solver = CaptchaSolver()

# Pydantic models for API
class Station(BaseModel):
    id: int
    name: str

class BookingRequest(BaseModel):
    start_station: int
    dest_station: int
    outbound_date: str
    outbound_time: str # e.g., "1200A" or "12:00" -> logic needs to handle format
    adult_num: str = "1F"
    personal_id: str
    phone: str
    seat_prefer: Optional[str] = "radio16" # radio16=None, radio17=Window, radio18=Aisle
    
    # Optional ticket types
    child_ticket_num: Optional[str] = "0H"
    disabled_ticket_num: Optional[str] = "0W"
    elder_ticket_num: Optional[str] = "0E"
    college_ticket_num: Optional[str] = "0P"
    
    # Max delay time (Latest acceptable arrival/departure? Logic says departure hour)
    outbound_delay_time: Optional[str] = "23" 
    
    # Optional preferred train numbers (comma separated)
    preferred_trains: Optional[str] = None 

class BookingResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None

@app.get("/api/stations")
def get_stations():
    from thsr_ticket.configs.web.enums import StationMapping
    return [{"id": s.value, "name": s.name} for s in StationMapping]

@app.get("/api/history")
def get_history():
    return [r._asdict() for r in db.get_history()]

def convert_time_format(time_str: str) -> str:
    """
    Convert 24h time string (e.g. "1700", "0630", "1200") 
    to THSR format (e.g. "500P", "630A", "1200N").
    
    THSR Rules based on AVAILABLE_TIME_TABLE:
    - 00:00 - 11:59 -> A (except 12:xx AM is 12xxA)
    - 12:00 -> 1200N
    - 12:01 - 12:59 -> 12xxP (Actually 1230P exists, 1201A exists?)
      Let's check table: 1201A (00:01?), 1230A (00:30?), 600A... 
      1200N (Noon), 1230P (12:30 PM), 100P
    
    Wait, "1201A" usually means 00:01. "1230A" means 00:30.
    "1200N" is Noon.
    "1230P" is 12:30 PM.
    "100P" is 13:00.
    """
    if not time_str:
        return "1200N" 
        
    # Handle "1200" -> "1200N" special case
    if time_str == "1200":
        return "1200N"
    
    try:
        hour = int(time_str[:-2])
        minute = time_str[-2:]
        
        if hour == 12:
            return f"12{minute}P" # 1230 -> 1230P
        elif hour > 12:
            return f"{hour-12}{minute}P" # 1300 -> 100P
        else:
            # hour < 12. 
            # Note: 00:xx -> 12xxA? 
            # Frontend starts from 05:00 (500).
            # "500" -> "500A"
            return f"{hour}{minute}A"
    except:
        return time_str

@app.post("/api/book")
def book_ticket(req: BookingRequest):
    logger.info(f"Received booking request: {req}")
    
    # 1. Construct Record object
    formatted_time = convert_time_format(req.outbound_time)
    
    record = Record(
        personal_id=req.personal_id,
        phone=req.phone,
        start_station=req.start_station,
        dest_station=req.dest_station,
        outbound_time=formatted_time,
        adult_num=req.adult_num,
        outbound_date=req.outbound_date,
        child_ticket_num=req.child_ticket_num,
        disabled_ticket_num=req.disabled_ticket_num,
        elder_ticket_num=req.elder_ticket_num,
        college_ticket_num=req.college_ticket_num,
        outbound_delay_time=req.outbound_delay_time,
        preferred_trains=req.preferred_trains.split(',') if req.preferred_trains else None,
    )
    
    # Check if seat_prefer needs to be handled via wrapper if Record doesn't support it
    # But wait, original Record assumes seat_prefer is handled by interactive flow or passed elsewhere.
    # We used a wrapper in previous step.
    
    class RecordWrapper:
        def __init__(self, record_data, seat_prefer):
            self._record = record_data
            self.seat_prefer = seat_prefer
        
        def __getattr__(self, name):
            return getattr(self._record, name)
            
    wrapped_record = RecordWrapper(record, req.seat_prefer)

    # 2. Run Flow
    # We replicate BookingFlow.run but use NonInteractiveFirstPageFlow
    try:
        client = HTTPRequest()
        error_feedback = ErrorFeedback()
        
        def check_error(resp_content):
            errors = error_feedback.parse(resp_content)
            if errors:
                return [e.msg for e in errors]
            return None
        
        # Step 1: First Page
        flow1 = NonInteractiveFirstPageFlow(client, record=wrapped_record, captcha_solver=captcha_solver)
        book_resp, book_model, updated_record = flow1.run()
        
        if errs := check_error(book_resp.content):
             return BookingResponse(status="error", message="Booking failed at step 1 (Options)", data={"html": str(book_resp.content), "errors": errs})

        # Step 2: Confirm Train
        # We need ConfirmTrainFlow to auto-select. 
        # By default currently logic selects first one.
        train_resp, train_model = ConfirmTrainFlow(client, book_resp, record=updated_record).run()
        if errs := check_error(train_resp.content):
             return BookingResponse(status="error", message="Booking failed at step 2 (Train)", data={"html": str(train_resp.content), "errors": errs})

        # Step 3: Confirm Ticket
        ticket_resp, ticket_model = ConfirmTicketFlow(client, train_resp, updated_record).run()
        if errs := check_error(ticket_resp.content):
             return BookingResponse(status="error", message="Booking failed at step 3 (Ticket)", data={"html": str(ticket_resp.content), "errors": errs})

        # Result
        result_model = BookingResult().parse(ticket_resp.content)
        # BookingResult.parse returns a list [Ticket]
        # Ticket is a namedtuple
        if isinstance(result_model, list) and result_model:
            ticket = result_model[0]
            # namedtuple has _asdict(), not dict()
            data = ticket._asdict()
        else:
            data = {}
        
        # Save history
        db.save(updated_record, ticket_model)
        
        return BookingResponse(status="success", message="Booking Submitted", data=data)

    except Exception as e:
        error_msg = str(e)
        # Check for known errors to suppress stack trace
        known_errors = [
            "Preferred trains", "Tailless-Sold out", "system is busy", 
            "系統忙碌", "sold out", "不再提供網路訂位",
            "No available trains", "太晚了", "超過限制時間", 
            "timed out", "timestamp", "Max retries exceeded"
        ]
        if any(k in error_msg for k in known_errors):
            logger.warning(f"Booking suppressed error: {error_msg}")
        else:
            logger.error(f"Booking error: {e}", exc_info=True)
            
        return BookingResponse(status="error", message=error_msg)
    finally:
        if 'client' in locals() and hasattr(client, 'close'):
            client.close()

from fastapi.staticfiles import StaticFiles
try:
    # Mount static files at root
    app.mount("/", StaticFiles(directory="web", html=True), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
