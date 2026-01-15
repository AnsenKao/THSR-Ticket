import logging
import time
import random
from typing import Optional

from thsr_ticket.controller.booking_flow import BookingFlow
from thsr_ticket.model.db import ParamDB, Record
from thsr_ticket.ml.model import CaptchaSolver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        # logging.FileHandler("booking.log")
    ]
)
logger = logging.getLogger(__name__)

class BookingSystem:
    def __init__(self):
        self.db = ParamDB()
        self.record: Optional[Record] = None
        self.captcha_solver = CaptchaSolver() # Load model once
        self.flow: Optional[BookingFlow] = None

    def start(self):
        logger.info("Starting THSR Ticket Booking System...")
        
        # Load history record if available
        self.record = self.db.get_history_record()
        if self.record:
            logger.info(f"Loaded history record for ID: {self.record.personal_id}")
        else:
            logger.info("No history record found. Please enter details.")

        self.loop()

    def loop(self):
        attempt_count = 0
        while True:
            try:
                attempt_count += 1
                logger.info(f"Booking attempt #{attempt_count}")
                
                # Re-initialize BookingFlow for each attempt to reset session state if needed,
                # but reuse record and captcha_solver
                self.flow = BookingFlow(record=self.record, captcha_solver=self.captcha_solver)
                
                result = self.flow.run()
                
                # Update record with the one from flow (schema might have changed/filled)
                if self.flow.record:
                    self.record = self.flow.record

                if result == 'Finish':
                    logger.info("Booking completed successfully!")
                    break
                
                # If run returns something else (e.g. error page response but handled), 
                # usually BookingFlow returns 'Finish' on success or loops internally?
                # Actually BookingFlow.run returns Response object for errors?
                # Original code: if status == 'Finish': break. 
                # Else it returns response object? 
                # BookingFlow.run: 
                # if show_error returns True, it returns resp.
                # if success, returns 'Finish'.
                
                if result != 'Finish':
                    logger.warning("Booking failed (Error detected). Retrying...")
                    # If it returns a Response, it means an error occurred and was shown.
                    # We retry.

                time.sleep(random.uniform(1, 3))

            except KeyboardInterrupt:
                logger.info("Booking stopped by user.")
                break
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}", exc_info=True)
                time.sleep(random.uniform(1, 3))

if __name__ == "__main__":
    bot = BookingSystem()
    bot.start()
