Integration of Calendar (.ics) with Toggl specifically for use by students of Carnegie Mellon University.

This project is written in Python using Flask framework.

### Code Structure ###

worker.py - Setup as a cron which queries from events table to create time entries in Toggl
<br/>toggltartan.py - The main controller file which handles requests from the frontend
