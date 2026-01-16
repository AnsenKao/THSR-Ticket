
import asyncio
import aiohttp
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("batch_book")

# Station Mapping for reference
# Taipei = 2
# Zuouing = 12
# Hsinchu = 5

REQUESTS = [
    {
        "note": "2/13 Taipei to Zuouing, After 18:50",
        "start_station": 2,
        "dest_station": 12,
        "outbound_date": "2026-02-13",
        "outbound_time": "1900", # Adjusted to 19:00 (700P) as 18:50 is not a valid slot
        "adult_num": "1F",
        "personal_id": "E125274494",
        "phone": "0931875346",
        "outbound_delay_time": "21"
    },
    # {
    #     "note": "2/17 (Tue) Zuouing to Taipei, 6 Adult tickets, noon",
    #     "start_station": 12,
    #     "dest_station": 2,
    #     "outbound_date": "2026-02-17",
    #     "outbound_time": "1200", 
    #     "adult_num": "6F",
    #     "personal_id": "E125274494",
    #     "phone": "0931875346"
    # },
    # {
    #     "note": "2/18 (Wed) Taipei to Zuouing, 6 Adult tickets, 15:30-16:30",
    #     "start_station": 2,
    #     "dest_station": 12,
    #     "outbound_date": "2026-02-18",
    #     # 15:30-16:30 range. We pick 15:30 (1530)
    #     "outbound_time": "1530",
    #     "adult_num": "6F",
    #     "personal_id": "E125274494",
    #     "phone": "0931875346"
    # },
    {
        "note": "2/22 Zuouing to Hsinchu, After 14:00",
        "start_station": 12,
        "dest_station": 5, # Hsinchu
        "outbound_date": "2026-02-22",
        "outbound_time": "1400",
        "adult_num": "1F",
        "personal_id": "E125274494",
        "phone": "0931875346",
        "outbound_delay_time": "16"
    }
]


async def book(session, req):
    url = "http://localhost:8000/api/book"
    # Filter out 'note' key
    payload = {k: v for k, v in req.items() if k != 'note'}
    
    # Defaults
    if 'seat_prefer' not in payload:
        payload['seat_prefer'] = 'radio16' # None
    if 'child_ticket_num' not in payload:
        payload['child_ticket_num'] = '0H'
        
    while True:
        try:
            logger.info(f"🚀 Sending request: {req['note']}")
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                if data.get('status') == 'success':
                    logger.info(f"✅ Success: {req['note']}")
                    break # Exit loop on success
                else:
                    error_msg = data.get('message')
                    error_details = data.get('data', {}).get('errors', [])
                    logger.warning(f"⚠️ Failed: {req['note']} - {error_msg}")
                    if error_details:
                        logger.warning(f"   Reason: {error_details}")
                    
                    logger.info(f"⏳ Retrying {req['note']} in 5 seconds...")
                    await asyncio.sleep(5) # Wait before retry
        except Exception as e:
            logger.error(f"❌ Error: {req['note']} - {e}")
            await asyncio.sleep(5)

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [book(session, req) for req in REQUESTS]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    # We use a placeholder ID in the script. 
    # In a real scenario, the user might want to provide their own ID.
    # For now, we assume this is a demo or the user will update the script.
    print("Starting batch booking...")
    asyncio.run(main())
