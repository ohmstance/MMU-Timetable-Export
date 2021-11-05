import mmu_ics
import datetime
import getpass
import asyncio

FILE_NAME = "mmutimetable.ics"

student_id = input("Enter student ID: ")
password = getpass.getpass()

try:
    # I think asyncio.run closes too early for aiohttp to clean up connections on Windows. Do this instead.
    timetable = asyncio.get_event_loop().run_until_complete(mmu_ics.get_timetable_mmumobileapi(student_id, password))
except mmu_ics.RateLimitError:
    print("Rate limited. Try again later.")
    exit()
if not timetable:
    print("Credentials are invalid, or something wrong happened. Try again.")
    exit()

date_start = datetime.date.fromisoformat(input("Enter start date (YYYY-MM-DD): "))
date_stop = datetime.date.fromisoformat(input("Enter stop date (YYYY-MM-DD): "))

with open(FILE_NAME, "wb") as f:
    f.write(mmu_ics.ics_from_timetable(timetable, date_start, date_stop).getbuffer())
print(f"Exported as {FILE_NAME}")