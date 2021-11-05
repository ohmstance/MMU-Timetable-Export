# MMU-Timetable-Export
This script eases scheduling of classes from MMU course timetable to a calendar. It exports the calendar into a .ics (iCalendar) file format. The script schedules classes as a recurring weekly event.

Provide the following:
1. MMLS Student ID
2. MMLS Password
3. The date the first class starts in the trimester
4. The date the latest class ends in the trimester

Dates are obtainable from MMU CMS. The script is only able to obtain timetable from MMU Mobile API once the trimester has started.

### Dependencies
1. aiohttp
2. iCalendar

Install dependencies with: `pip install -r requirements.txt`