import sys
sys.path.append("./")

from thsr_ticket.booking_system import BookingSystem

def main():
    print("Initializing...")
    bot = BookingSystem()
    bot.start()

if __name__ == "__main__":
    main()