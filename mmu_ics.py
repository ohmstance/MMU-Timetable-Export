from icalendar import Calendar, Event
from datetime import datetime, date, timezone, timedelta, time
from typing import (
    Union,
    List,
    Dict,
)
import asyncio
import aiohttp
import json
import os
import io

# ALIASES

MMUMobileAPITimetable = List[List[Dict[str, str]]]

# EXCEPTIONS

class RateLimitError(Exception):
    """
    Rate-limited by MMU Mobile API.
    """

    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message

# FUNCTIONS

async def get_timetable_mmumobileapi(student_id: str, password: str,
                                     connector: aiohttp.TCPConnector = None) -> MMUMobileAPITimetable:
    """
    Returns a Python representation of mmumobileapi timetable API json-formatted response.

    student_id  MMLS student ID
    password    MMLS password
    connector   pass aiohttp.TCPConnector object to share connection
    """

    connector_owner = False
    if connector is None:
        connector = aiohttp.TCPConnector()
        connector_owner = True
    async with aiohttp.ClientSession(connector=connector, connector_owner=connector_owner) as session:
        data = {'username': student_id, 'password': password, 'id': 'asd'}
        async with session.post("https://mmumobileapps.mmu.edu.my/api/auth/login2", data=data) as response:
            if response.status != 200:
                return [] # Return empty list if login unsuccessful
            token = json.loads(await response.text())["token"]
        params = {'token': token}
        async with session.get("https://mmumobileapps.mmu.edu.my/api/camsys/student_key", params=params) as response:
            if response.status != 200:
                # Token required
                return []
            response_text = await response.text()
            if response_text == '03':
                raise RateLimitError("Unable to obtain student_token due to rate limit. Try again later.")
            student_token = response_text
        async with session.get(f"https://mmumobileapps.mmu.edu.my/api/camsys/timetable/{student_token}",
                               params=params) as response:
            if response.status != 200:
                # Invalid token or token required
                return []
            timetable = json.loads(await response.text())
            if isinstance(timetable, dict):
                # Invalid student key
                return []
        async with session.post("https://mmumobileapps.mmu.edu.my/api/logout", params=params) as response:
            # Logout
            pass

    return timetable

def ics_from_timetable(mmumobileapi_timetable: Union[str, io.TextIOBase, MMUMobileAPITimetable],
                       date_start: date, date_stop: date) -> io.BytesIO:
    """
    Returns a io.BytesIO object that is a .ics file containing programmatically created class events starting from
    date_start until date_stop.

    mmumobileapi_timetable      json-formatted response from mmumobileapi timetable API
    date_start                  cut-off start date for calendar events creation
    date_stop                   cut-off stop date for calendar events creation

    mmumobileapi_timetable format:
    [
        [
            {
                 "day": "Monday",
                 "start": "14:00",
                 "end": "17:00",
                 "subject_name": "SUBJECT NAME",
                 "subject_code": "EEE1234",
                 "type": "LEC",
                 "venue": "FOEVC0123",
                 "section": "EC01",
                 "strm": "2110"
            }, ...
        ], ...
    ]
    """

    if isinstance(mmumobileapi_timetable, str):
        timetable = json.loads(mmumobileapi_timetable)
    elif isinstance(mmumobileapi_timetable, io.TextIOBase):
        timetable = json.load(mmumobileapi_timetable)
    elif isinstance(mmumobileapi_timetable, list):
        timetable = mmumobileapi_timetable
    else:
        raise TypeError(
            f"'str', 'list', or file-like object expected, not {type(mmumobileapi_timetable)} object."
        )

    # Flatten timetable events list from a list of list of dict into a list of dict
    timetable_flattened = (event for day in timetable for event in day)

    # Defaults to case where date_start is on a Monday. Used to offset number of days to obtain a date with a certain
    # day from date_start where offset_date > date_start and offset_date is nearest to date_start.
    weekday_offset = {
        'Monday': 0,
        'Tuesday': 1,
        'Wednesday': 2,
        'Thursday': 3,
        'Friday': 4,
        'Saturday': 5,
        'Sunday': 6,
    }

    # Generates offsets to offset weekdays starting before date_start to start on the same day next week. Normalizes
    # day of start_date in weekday_offset to 0.
    weekday_offset = {day_str: weekday - date_start.weekday() for day_str, weekday in weekday_offset.items()}
    weekday_offset = {day_str: weekday + 7 if weekday < 0 else weekday for day_str, weekday in weekday_offset.items()}

    # General iCalendar properties
    cal = Calendar()
    cal.add('prodid', '-//RAAZ//MMLS-Attendance-Grabber//')
    cal.add('version', '2.0')

    # datetime.timezone object with offset from UTC for Malaysian Standard Time (MST)
    tzinfo = timezone(timedelta(hours=8), name="Malaysian Standard Time (MST)")

    for e in timetable_flattened:
        event = Event()
        event.add('summary', f"{e['subject_code']} {e['subject_name']}") # Event title
        event.add('description', f"{e['section']} - {e['venue']}") # Event description

        dclass = date_start + timedelta(days=weekday_offset[e['day']])
        if dclass > date_stop:
            # Event is after date_stop. Don't add this event to calendar.
            continue

        tstart = time.fromisoformat(e['start'])
        dtstart = datetime(dclass.year, dclass.month, dclass.day, tstart.hour, tstart.minute, tzinfo=tzinfo)
        event.add('dtstart', dtstart) # Event start datetime

        tstop = time.fromisoformat(e['end'])
        dtstop = datetime(dclass.year, dclass.month, dclass.day, tstop.hour, tstop.minute, tzinfo=tzinfo)
        event.add('dtend', dtstop) # Event stop datetime

        event.add('dtstamp', datetime.now(tz=tzinfo)) # Event-creation timestamp

        dtuntil = datetime(date_stop.year, date_stop.month, date_stop.day, 23, 59, 59, tzinfo=tzinfo)
        event.add('rrule', {'freq': 'weekly', 'until': dtuntil}) # Recurrence rule

        cal.add_component(event) # Adds event to calendar

    return io.BytesIO(cal.to_ical())




