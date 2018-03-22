import requests
import json
import pymysql.cursors
import time
import datetime
import arrow


def create_time_entry(api_token, description, project_id, from_arrow, to_arrow):
    params = {}
    # {"time_entry":{"description":"Meeting with possible clients","tags":["toggltartan"],"duration":4800,"start":"2018-02-13T07:58:58.000Z","pid":94945801,"created_with":"toggltartan"}}

    from_arrow = from_arrow.replace(tzinfo="America/New_York")
    to_arrow = to_arrow.replace(tzinfo="America/New_York")

    params['description'] = description
    params['tags'] = '["toggl-tartan"]'

    params['start'] = from_arrow.isoformat()
    params['duration'] = (to_arrow - from_arrow).seconds

    if (project_id is not None):
        params['pid'] = project_id

    params['created_with'] = "toggl-tartan"

    data_dict = {}
    data_dict['time_entry'] = params
    data = json.dumps(data_dict)

    headers = {'Content-Type': 'application/json'}
    r = requests.post("https://www.toggl.com/api/v8/time_entries", headers=headers, auth=(api_token, 'api_token'), data=data)

    if (r.status_code == 200):
        print(time.strftime("%Y-%m-%d %H:%M:%s") + " - Created time entry - api_token=[" + api_token + "], description=[" + description + "], project_id=[" +
              str(project_id) + "], start_arrow=[" + from_arrow.isoformat() + "], stop_arrow=[" + to_arrow.isoformat() + "]")
    else:
        print(time.strftime("%Y-%m-%d %H:%M:%s") + " - ERROR Failed to create time entry - api_token=[" + api_token + "], description=[" + description + "], " +
              "project_id=[" + str(
            project_id) + "], start_arrow=[" + from_arrow.isoformat() + "], stop_arrow=[" + to_arrow.isoformat() + "]. Response status code=[" + str(
            r.status_code) + "], " +
              "response text=[" + str(r.content) + "]")

    return


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
            # Ugly hack to handle case when run_to_date_time is Y-m-d 00:00:00
            if run_to_date_time.strftime("%H:%M:%S") != "00:00:00":
                cur.execute(
                    "select course_id, name, start_time, end_time, frequency, from_date, till_date, days_of_week, toggl_project_id from events where user_id = %s and is_active = 1 and"
                    " (from_date <= %s and till_date >= %s and start_time >= %s and start_time <= %s)",
                    (user_row['id'], run_from_date_time.strftime("%Y-%m-%d"), run_to_date_time.strftime("%Y-%m-%d"), run_from_date_time.strftime("%H:%M:%S"),
                     run_to_date_time.strftime("%H:%M:%S")))
            else:
                cur.execute(
                    "select course_id, name, start_time, end_time, frequency, from_date, till_date, days_of_week, toggl_project_id from events where user_id = %s and is_active = 1 and"
                    " ((from_date <= %s and till_date >= %s and (start_time >= %s and start_time <= '23:59:59')) or (from_date <= %s and till_date >= %s and (start_time = '00:00:00')))",
                    (user_row['id'], run_from_date_time.strftime("%Y-%m-%d"), run_from_date_time.strftime("%Y-%m-%d"), run_from_date_time.strftime("%H:%M:%S"),
                     run_to_date_time.strftime("%Y-%m-%d"), run_to_date_time.strftime("%Y-%m-%d")))

            event_rows = cur.fetchall()

            for event_row in event_rows:

                if event_row['frequency'] == "onetime":
                    from_arrow = arrow.get(str(event_row['from_date']) + " " + str(event_row['start_time']), "YYYY-MM-DD H:mm:ss")
                    to_arrow = arrow.get(str(event_row['till_date']) + " " + str(event_row['end_time']), "YYYY-MM-DD H:mm:ss")

                    create_time_entry(user_row['api_token'], event_row['name'], event_row['toggl_project_id'], from_arrow, to_arrow)

                elif event_row['frequency'] == "daily" or event_row['frequency'] == "weekly":

                    from_arrow = arrow.get(run_from_date_time.strftime("%Y-%m-%d") + " " + str(event_row['start_time']), "YYYY-MM-DD H:mm:ss")

                    # To handle case when event starts at say 00:00
                    if from_arrow < arrow.get(str(run_from_date_time), "YYYY-MM-DD HH:mm:ss"):
                        from_arrow = from_arrow.replace(days=+1)

                    if event_row['frequency'] == "weekly":
                        day_of_week = int(from_arrow.format('d'))
                        day_of_week_mask = 1 << (7 - day_of_week)

                        if ((day_of_week_mask & event_row['days_of_week']) == 0):
                            continue

                    # To handle case when event starts at say 23:30 and goes on till 00:30 the next day
                    if event_row['start_time'] > event_row['end_time']:
                        print(from_arrow.replace(days=+1).format('YYYY-MM-DD') + " " + str(event_row['end_time']))
                        to_arrow = arrow.get(from_arrow.replace(days=+1).format('YYYY-MM-DD') + " " + str(event_row['end_time']), "YYYY-MM-DD H:mm:ss")
                    else:
                        to_arrow = arrow.get(from_arrow.format('YYYY-MM-DD') + " " + str(event_row['end_time']), "YYYY-MM-DD H:mm:ss")

                    # Create a proper description from the event name for events created by Canvas.
                    # This is needed only for weekly events as ics file created by canvas only contains weekly events
                    if event_row['frequency'] == "weekly":
                        description = form_time_entry_description(event_row['course_id'], event_row['name'])
                    else:
                        description = event_row['name']

                    create_time_entry(user_row['api_token'], description, event_row['toggl_project_id'], from_arrow, to_arrow)

                elif event_row['frequency'] == "monthly":
                    # Not implemented currently
                    pass

    return


# Round down to closest minute
# tm = datetime.datetime.now()
tm = datetime.datetime(2018, 2, 14, hour=8, minute=00, second=0)

run_end_date_time = tm - datetime.timedelta(seconds=tm.second, microseconds=tm.microsecond)

run_start_date_time = run_end_date_time - datetime.timedelta(minutes=4, seconds=59)

print(
    time.strftime("%Y-%m-%d %H:%M:%S") + " - Starting run for [" + run_start_date_time.strftime("%Y-%m-%d %H:%M:%S") + "] to [" + run_end_date_time.strftime(
        "%Y-%m-%d %H:%M:%S") + "]")

run(run_start_date_time, run_end_date_time)

print(
    time.strftime("%Y-%m-%d %H:%M:%S") + " - Finished run for [" + run_start_date_time.strftime("%Y-%m-%d %H:%M:%S") + "] to [" + run_end_date_time.strftime(
        "%Y-%m-%d %H:%M:%S") + "]")
