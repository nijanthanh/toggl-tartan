from ics import Calendar
import requests
import json
import pymysql.cursors
import time
import datetime
import arrow

# fp = open('canvas.ics', 'rb')
fp = open('google-calendar.ics', 'rb')
data = fp.read()

c = Calendar(data.decode("utf-8"))

begin_date = ""


def create_time_entry(api_token, description, project_id, start_arrow, stop_arrow):
    params = {}
    # {"time_entry":{"description":"Meeting with possible clients","tags":["toggltartan"],"duration":4800,"start":"2018-02-13T07:58:58.000Z","pid":94945801,"created_with":"toggltartan"}}
    params['description'] = description
    params['tags'] = '["toggl-tartan"]'

    # params['start'] = "2018-02-13T07:58:58.000Z"
    params['start'] = start_arrow.isoformat
    params['stop'] = stop_arrow.isoformat

    if (project_id is not None):
        params['pid'] = project_id

    params['created_with'] = "toggl-tartan"

    dataDict = {}
    dataDict['time_entry'] = params
    data = json.dumps(dataDict)

    headers = {'Content-Type': 'application/json'}
    r = requests.post("https://www.toggl.com/api/v8/time_entries", headers=headers, auth=(api_token, 'api_token'), data=data)
    # x = r.json()
    print(r.text)
    if (r.status_code == 200):
        print(time.strftime("%Y-%m-%d %H:%M:%s"))
    else:
        print(time.strftime("%Y-%m-%d %H:%M:%s"))

    return


def get_project_id(course_id, user_id):
    project_id = None


    return project_id


def create_db_connection():
    # Ideally read this from file pointed TOGGLTARTAN_SETTINGS
    connection = pymysql.connect(host='localhost',
                                 user='toggl',
                                 password='toggl',
                                 db='toggltartan',
                                 charset='utf8',
                                 cursorclass=pymysql.cursors.DictCursor)

    # Not explicitly closing the connection as it will anyway close when script execution finishes
    return connection


def form_time_entry_description(course_id, event_name):
    if event_name == "Analysis of Software Artifacts :: 17654 A":
        description = "Recitation"
    elif event_name == "Analysis of Software Artifacts :: 17654 1":
        description = "Lecture"
    elif event_name == "Architectures for Software Systems :: 17655 A":
        description = "Recitation"
    elif event_name == "Architectures for Software Systems :: 17655 1":
        description = "Lecture"
    elif event_name == "Communication for Software Engineers II:: 17657 A":
        description = "Lecture"
    elif (" :: " + course_id.replace("-", "")) in event_name:
        description = "Lecture/recitation"
    else:
        description = event_name

    return description



def run(run_from_date_time, run_to_date_time):
    conn = create_db_connection()

    with conn.cursor() as cur:
        cur.execute("select id, api_token from users where is_active = 1 order by id")
        user_rows = cur.fetchall()

        for user_row in user_rows:
            cur.execute(
                "select course_id, name, start_time, end_time, frequency, from_date, till_date, days_of_week from events where user_id = %s and is_active = 1 and"
                " (from_date <= %s and till_date >= %s and start_time >= %s and start_time <= %s",
                (user_row['id'], run_from_date_time.strftime("%Y-%m-%d"), run_to_date_time.strftime("%Y-%m-%d"), run_from_date_time.strftime("%H:%M:%S"),
                 run_to_date_time.strftime("%H:%M:%S")))
            event_rows = cur.fetchall()

            for event_row in event_rows:
                project_id = get_project_id(user_row['course_id'], user_row['id'])

                if event_row['frequency'] == "onetime":
                    from_arrow= arrow.get(event_row['from_date'] + " " + event_row['start_time'], "YYYY-MM-DD HH:mm:ss")
                    to_arrow = arrow.get(event_row['till_date'] + " " + event_row['end_time'], "YYYY-MM-DD HH:mm:ss")

                    create_time_entry(user_row['api_token'], user_row['name'], project_id, from_arrow, to_arrow)

                elif event_row['frequency'] == "daily":
                    create_time_entry(api_token, description, project_id, start_time, duration)
                elif event_row['frequency'] == "weekly":
                    # Create a proper description from the event name for events created by Canvas.
                    # This is needed only for weekly events as ics file created by canvas only contains weekly events
                    form_time_entry_description(event_row['course_id'], event_row['name'])

    # if frequency == "onetime":
    #     # good to go
    # if frequency == "daily":
    #     # good to go as well
    # elif frequency == "weekly":
    #     get current day_of_week
    #     mask = get_mask("day")
    #
    #     if mask == (day_of_week & mask):
    #         # create_task
    # elif frequency == "monthly":
    #     # Not implemented currently
    #     pass
    #
    # form_event_name()

    return


# Round down to closest minute
tm = datetime.datetime.now()
run_start_date_time = tm - datetime.timedelta(seconds=tm.second, microseconds=tm.microsecond)

run_end_date_time = run_start_date_time - datetime.timedelta(minutes=4, seconds=59)

# print(
#     time.strftime("%Y-%m-%d %H:%M:%S") + " - Starting run for [" + fromDateTime.strftime("%Y-%m-%d %H:%M:%S") + "] to [" + toDateTime.strftime("%Y-%m-%d %H:%M:%S") + "]")
#
# run(fromDateTime, toDateTime)
#
# print(
#     time.strftime("%Y-%m-%d %H:%M:%S") + " - Finished run for [" + fromDateTime.strftime("%Y-%m-%d %H:%M:%S") + "] to [" + toDateTime.strftime("%Y-%m-%d %H:%M:%S") + "]")

#
# fromTime = "2018-02-22 22:30:00"
# diff =  arrow.get(fromTime,  'YYYY-MM-DD HH:mm:ss')
# x = diff.isoformat()
# print(x)