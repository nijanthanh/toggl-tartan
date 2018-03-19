Integration of Calendar (.ics) with Toggl specifically for use of students of Carnegie Mellon University students.

This project is written in Python using Flask framework.

Code Structure -
worker.py - Setup as a cron which queries from events table to create time entries in Toggl
toggltartan.py - The main controller file which handles requests from the frontend
