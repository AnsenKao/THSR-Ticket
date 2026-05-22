from enum import Enum


class StationMapping(Enum):
    南港 = 1
    台北 = 2
    板橋 = 3
    桃園 = 4
    新竹 = 5
    苗栗 = 6
    台中 = 7
    彰化 = 8
    雲林 = 9
    嘉義 = 10
    台南 = 11
    左營 = 12


class TicketType(Enum):
    ADULT = 'F'
    CHILD = 'H'
    DISABLED = 'W'
    ELDER = 'E'
    COLLEGE = 'P'
