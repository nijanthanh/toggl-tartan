import os
import json
import re
import arrow

from tt.toggl_helper import *
from flask import Flask, render_template, request, jsonify, logging, url_for
from flask_mysqldb import MySQL
from ics import Calendar
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = set(['ics'])

mysql = MySQL()

app = Flask(__name__)
app.config.from_object(__name__)

app.config.from_envvar('TOGGLTARTAN_SETTINGS')  # silent=True)
mysql.init_app(app)


def create_db_connection():
    conn = mysql.connect
    conn.autocommit(True)
    cur = conn.cursor()
    return cur


def create_or_update_user(api_token):
    cur = create_db_connection()

    cur.execute("select id from users where api_token = %s and is_active = 1 order by id desc limit 1", [api_token])
    rv = cur.fetchone()

    user_data_dict = get_current_user_data(api_token)

    primary_workspace_id = -1

    for workspace in user_data_dict['data']['workspaces']:
        if ("MSE" in workspace['name']) or ("MSIT" in workspace['name']):
            primary_workspace_id = workspace['id']
            break

    if rv is not None:
        cur.execute("update users set toggl_id = %s, email = %s, name = %s, toggl_workspace_id = %s, date_updated = now() where id = %s",
                    (user_data_dict['data']['id'], user_data_dict['data']['email'], user_data_dict['data']['fullname'], primary_workspace_id, rv[0]))

        # If another user table entry exists with same api_token, mark it as inactive
        cur.execute("update users set is_active = 0, date_updated = now() where id != %s and api_token = %s",
                    (rv[0], api_token))

        user_id = rv[0]
    else:
        cur.execute("insert into users(api_token, toggl_id, email, name, is_active, toggl_workspace_id, date_created, date_updated) values (%s, %s, %s, %s, 1, %s, now(), now())",
                    (user_data_dict['data']['api_token'], user_data_dict['data']['id'], user_data_dict['data']['email'],
                     user_data_dict['data']['fullname'], primary_workspace_id))
        user_id = cur.lastrowid

    data = {'user_id': user_id, 'primary_workspace_id': primary_workspace_id, 'name': user_data_dict['data']['fullname']}

    return ("success", json.dumps(data))


def create_projects(api_token, user_id, toggl_workspace_id):
    cur = create_db_connection()

    cur.execute("delete from projects where user_id = %s", [user_id])

    projects_list = get_workspace_projects_data(api_token, str(toggl_workspace_id))

    for project in projects_list:
        cur.execute("insert into projects(user_id, name, toggl_project_id, is_active, date_created, date_updated) values (%s, %s, %s, 1, now(), now())",
                    (user_id, project['name'], project['id']))

    return ("success", json.dumps({}))


def get_toggl_project_id_for_course(course_id, user_id):
    cur = create_db_connection()

    # Map Software Engineering Bootcamp course to the "MSIT/MSE project" project
    if course_id != "17-676":
        cur.execute("select toggl_project_id from projects where user_id = %s and name like %s", (user_id, course_id + '%'))
    else:
        cur.execute("select toggl_project_id from projects where user_id = %s and (name like %s or name like %s)", (user_id, "17-671%", "17-677%"))

    rv = cur.fetchone()

    if rv is None:
        toggl_project_id = None
    else:
        toggl_project_id = rv[0]

    return toggl_project_id


# Return decimal version of bit-wise representation
# Week starts with Monday
# Eg. 64 (1000000) refers to Mo
#     65 (1000001) refers to Mo,Su
def get_days_of_week(days_of_week_list):
    days_of_week = 0

    for day in days_of_week_list:
        if day == "mo":
            days_of_week = days_of_week | (1 << 6)
        elif day == "tu":
            days_of_week = days_of_week | (1 << 5)
        elif day == "we":
            days_of_week = days_of_week | (1 << 4)
        elif day == "th":
            days_of_week = days_of_week | (1 << 3)
        elif day == "fr":
            days_of_week = days_of_week | (1 << 2)
        elif day == "sa":
            days_of_week = days_of_week | (1 << 1)
        elif day == "su":
            days_of_week = days_of_week | 1

    return days_of_week


def input_ics_file(api_token, calendar_file_path):
    cur = create_db_connection()

    with open(calendar_file_path) as f:
        calendar_data = f.read()

    if not calendar_data:
        raise (TogglTartanError("Oops! Could not read data from the .ics file"))

    c = Calendar(calendar_data)

    res = create_or_update_user(api_token)
    data = json.loads(res[1])
    user_id = data['user_id']

    create_projects(api_token, user_id, data['primary_workspace_id'])

    cur.execute("update events set is_active = 0, date_updated = now() where user_id = %s and is_active != 0", [user_id])

    malformed_events_list = []

    timezone = ""
    for key in c._timezones:
        #timezone = key

        # Hardcoding timezone. The above logic to find timezone is broken as the same calendar can have multiple timezone sections
        # If timezone is not set, do not set it
        timezone = "America/New_York"
        break



    for event in c.events:
        try:
            p = re.compile('\d{5}?')
            m = p.search(event.name)
            course_id_without_hyphen = m.group()
            course_id = course_id_without_hyphen[:2] + "-" + course_id_without_hyphen[2:]

            toggl_project_id = get_toggl_project_id_for_course(course_id, user_id)
        except:
            try:
                p = re.compile('\d{2}-\d{3}?')
                m = p.search(event.name)
                course_id = m.group()

                toggl_project_id = get_toggl_project_id_for_course(course_id, user_id)
            except:
                malformed_events_list.append(event.name)
                course_id = ""
                toggl_project_id = None
                app.logger.warning("Course ID could not be identified for event - " + event.name + ". Message=[" + json.dumps(
                    data) + "], Endpoint=[" + request.method + " " + request.path + "], Post data=[" + json.dumps(request.form) + "], Args=[" + json.dumps(
                    request.args) + "]")

        if timezone != "":
            event_begin_arrow = event.begin.to(timezone)
        else:
            event_begin_arrow = event.begin.replace(tzinfo="America/New_York")

        start_time = event_begin_arrow.format('HH:mm:ss')

        if timezone != "":
            event_end_arrow = event.end.to(timezone)
        else:
            event_end_arrow = event.end.replace(tzinfo="America/New_York")

        end_time = event_end_arrow.format('HH:mm:ss')

        try:
            p = re.compile('FREQ=[^;]*')
            m = p.search(event._unused[0].value)
            frequency = m.group().split("=")[1].lower()
        except:
            frequency = "onetime"

        from_date = event_begin_arrow.format('YYYY-MM-DD')

        if frequency == "onetime":
            till_date = from_date
            days_of_week = 0
        else:
            # end_date is considered different from till_date
            # till_date is last date on which event can start

            # Check if event start on one day and overflows to another day(s). If event starts and ends on same calendar day, then event_days is 0
            event_length_timedelta = arrow.get(event_end_arrow.format('YYYY-MM-DD'), 'YYYY-MM-DD') - arrow.get(from_date, 'YYYY-MM-DD')
            event_length_days = event_length_timedelta.days

            try:
                p = re.compile('UNTIL=[^;]*')
                m = p.search(event._unused[0].value)
                until_str = m.group().split("=")[1]
                # Assumed to be local time zone

                till_date = arrow.get(until_str, 'YYYYMMDD').replace(days=-event_length_days).format('YYYY-MM-DD')
            except:
                try:
                    p = re.compile('COUNT=[^;]*')
                    m = p.search(event._unused[0].value)
                    count_str = int(m.group().split("=")[1])
                    repeat_count = count_str - 1

                    if (frequency == "daily"):
                        till_date = event_begin_arrow.replace(days=+repeat_count).format('YYYY-MM-DD')
                    elif frequency == "weekly":
                        till_date = event_begin_arrow.replace(weeks=+repeat_count).format('YYYY-MM-DD')
                    elif frequency == "monthly":
                        till_date = event_begin_arrow.replace(months=+repeat_count).format('YYYY-MM-DD')

                except:
                    # No event repeat end date specified. So, repeat for 1 year from now
                    till_date = arrow.now("America/New_York").replace(years=+1).format('YYYY-MM-DD')

            # Monthly repeating events is not handled
            if frequency == "monthly":
                days_of_week = 0
            elif frequency == "daily":
                days_of_week = 127  # This value is not going to be used though
            elif frequency == "weekly":
                # Represented as a decimal value of binary value. Week starts on Monday.
                try:
                    p = re.compile('BYDAY=[^;]*')
                    m = p.search(event._unused[0].value)
                    days_of_week_str = m.group().split("=")[1].lower()
                    days_of_week_list = days_of_week_str.split(",")
                except:
                    # Get the day of the week of the start date of the event
                    day_of_week = event_begin_arrow.format("ddd")[:2].lower()  # Convert to 2 letter format from 3 letter format
                    days_of_week_list = [day_of_week]

                days_of_week = get_days_of_week(days_of_week_list)
            else:
                app.logger.error(
                    "Unknown frequency [" + frequency + "] - [" + event.name + "]. Message=[" + json.dumps(
                        data) + "], Endpoint=[" + request.method + " " + request.path + "], Post data=[" + json.dumps(request.form) + "], Args=[" + json.dumps(
                        request.args) + "]")
                days_of_week = 0

        cur.execute(
            "insert into events(user_id, is_active, course_id, name, start_time, end_time, frequency, from_date, till_date, days_of_week, toggl_project_id, date_created, date_updated) "
            "values(%s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())",
            (user_id, course_id, event.name, start_time, end_time, frequency, from_date, till_date, days_of_week, toggl_project_id))

    data = {'malformed_events_list': malformed_events_list}

    return ("success", json.dumps(data))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET'])
def main():
    return render_template('index.html')


@app.route('/upload_calendar_file/<api_token>', methods=['POST'])
def upload_calendar_file(api_token):
    try:
        # check if the post request has the file part
        if 'calendar_file_input' not in request.files:
            status = "error"
            data = "Please choose a calendar file to import."

            app.logger.info(
                "Message=[" + data + "], Endpoint=[" + request.method + " " + request.path + "], Post data=[" + json.dumps(
                    request.form) + "], Args=[" + json.dumps(request.args) + "]")

            return jsonify(status=status, data=data)


        file = request.files['calendar_file_input']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            status = "error"
            data = "Please choose a calendar file to import."

            app.logger.info(
                "Message=[" + data + "], Endpoint=[" + request.method + " " + request.path + "], Post data=[" + json.dumps(
                    request.form) + "], Args=[" + json.dumps(request.args) + "]")

            return jsonify(status=status, data=data)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            calendar_file_path = os.path.join(app.root_path, 'ics_files/' + api_token + "-" + filename)

            file.save(calendar_file_path)

        (status, data) = input_ics_file(api_token, calendar_file_path)
    except TogglTartanError as error:
        status = "error"
        data = error.value
        # Ideally modify the logger itself to have context about the request
        app.logger.info(
            "Message=[" + data + "], Endpoint=[" + request.method + " " + request.path + "], Post data=[" + json.dumps(
                request.form) + "], Args=[" + json.dumps(request.args) + "]")

    return jsonify(status=status, data=data)


@app.route('/submit_api_token', methods=['POST'])
def submit_api_token():
    # Validate POST data api_token
    try:
        (status, response_data) = create_or_update_user(request.form['api_token'])
        #name =
        data = json.dumps({})
    except TogglTartanError as error:
        status = "error"
        data = error.value
        # Ideally modify the logger itself to have context about the request
        app.logger.info(
            "Message=[" + data + "], Endpoint=[" + request.method + " " + request.path + "], Post data=[" + json.dumps(
                request.form) + "], Args=[" + json.dumps(request.args) + "]")

    # Make request to https://www.toggl.com/api/v8/me
    # If empty result, notify users. Else update users table.

    return jsonify(status=status, data=data)


@app.route('/event_data/<api_token>', methods=['GET'])
def get_event_data(api_token):
    cur = create_db_connection()

    cur.execute("select id from users where api_token = %s and is_active = 1 order by id desc limit 1", [api_token])
    rv = cur.fetchone()

    events_data_list = []

    if rv is not None:
        cur.execute("select name, start_time, end_time, frequency, from_date, till_date, days_of_week from events where user_id = %s and is_active = 1", [rv[0]])
        event_rows = cur.fetchall()

        for event_row in event_rows:
            event_data_dict = {}
            event_data_dict['className'] = "m-fc-event--light m-fc-event--solid-warning"

            event_data_dict['title'] = event_row[0]
            event_data_dict['description'] = event_row[0]

            if event_row[3] == "onetime":
                x = str(event_row[4]) + " " + str(event_row[1])

                event_data_dict['start'] = arrow.get(str(event_row[4]) + " " + str(event_row[1]), "YYYY-MM-DD H:mm:ss").isoformat()
                event_data_dict['end'] = arrow.get(str(event_row[5]) + " " + str(event_row[2]), "YYYY-MM-DD H:mm:ss").isoformat()

                events_data_list.append(event_data_dict.copy())

            elif event_row[3] == "daily" or event_row[3] == "weekly":
                from_date = arrow.get(str(event_row[4]), "YYYY-MM-DD")
                till_date = arrow.get(str(event_row[5]), "YYYY-MM-DD")

                current_date = from_date

                while (current_date <= till_date):
                    if (event_row[3] == "weekly"):
                        day_of_week = int(current_date.format('d'))
                        day_of_week_mask = 1 << (7 - day_of_week)

                        if ((day_of_week_mask & event_row[6]) == 0):
                            current_date = current_date.replace(days=+1)
                            continue

                    event_data_dict['start'] = arrow.get(str(current_date.format('YYYY-MM-DD')) + " " + str(event_row[1]), "YYYY-MM-DD H:mm:ss").isoformat()

                    if event_row[1] > event_row[2]:
                        end_date = current_date.replace(days=+1).format('YYYY-MM-DD')
                    else:
                        end_date = current_date.format('YYYY-MM-DD')

                    event_data_dict['end'] = arrow.get(str(end_date) + " " + str(event_row[2]), "YYYY-MM-DD H:mm:ss").isoformat()
                    events_data_list.append(event_data_dict.copy())

                    current_date = current_date.replace(days=+1)


            elif event_row[3] == "monthly":
                # Not implemented currently
                pass

    return jsonify(events_data_list)

if __name__ == "__main__":
#    app.run(debug=True)
    app.run()
