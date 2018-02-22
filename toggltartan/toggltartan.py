import os
import json
import re
import arrow

from toggltartan.toggl_helper import *
from flask import Flask, render_template, request, jsonify, logging
from flask_mysqldb import MySQL
from ics import Calendar

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

    cur.execute("select id from users where api_token = %s order by id desc limit 1", [api_token])
    rv = cur.fetchone()

    user_data_dict = get_current_user_data(api_token)

    if rv is not None:
        cur.execute("update users set toggl_id = %s, email = %s, name = %s, date_updated = now() where id = %s",
                    (user_data_dict['data']['id'], user_data_dict['data']['email'], user_data_dict['data']['fullname'], rv[0]))
        user_id = rv[0]
    else:
        cur.execute("insert into users(api_token, toggl_id, email, name, date_created, date_updated) values (%s, %s, %s, %s, now(), now())",
                    (user_data_dict['data']['api_token'], user_data_dict['data']['id'], user_data_dict['data']['email'],
                     user_data_dict['data']['fullname']))
        user_id = cur.lastrowid

    data = {'user_id': user_id}

    return ("success", json.dumps(data))


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


def input_ics_file():
    cur = create_db_connection()

    calendar_file = os.path.join(app.root_path, 'scripts/google-calendar.ics')

    with open(calendar_file) as f:
        calendar_data = f.read()

    if not calendar_data:
        raise (TogglTartanError("Oops! Could not read data from the .ics file"))

    c = Calendar(calendar_data)

    res = create_or_update_user(request.form['api_token'])
    data = json.loads(res[1])
    user_id = data['user_id']

    cur.execute("update events set is_active = 0, date_updated = now() where user_id = %s and is_active != 0", [user_id])

    malformed_events_list = []

    for event in c.events:
        try:
            p = re.compile('\d{5}?')
            m = p.search(event.name)
            course_id = m.group()
        except:
            malformed_events_list.append(event.name)
            course_id = ""
            app.logger.warning("Course ID could not be identified for event - " + event.name + ". Message=[" + json.dumps(data) + "], Endpoint=[" + request.method + " " + request.path + "], Post data=[" + json.dumps(request.form) + "], Args=[" + json.dumps(request.args) + "]")

        start_time = event.begin.format('HH:mm:ss')
        end_time = event.end.format('HH:mm:ss')

        try:
            p = re.compile('FREQ=[^;]*')
            m = p.search(event._unused[0].value)
            frequency = m.group().split("=")[1].lower()
        except:
            frequency = "onetime"

        from_date = event.begin.format('YYYY-MM-DD')

        if frequency == "onetime":
            till_date = from_date
            days_of_week = 0
        else:
            try:
                p = re.compile('UNTIL=[^;]*')
                m = p.search(event._unused[0].value)
                until_str = m.group().split("=")[1]
                till_date = arrow.get(until_str, 'YYYYMMDD').format('YYYY-MM-DD')
            except:
                app.logger.warning(
                    "Missing 'UNTIL' for a non-onetime event - " + event.name + ". Message=[" + json.dumps(
                        data) + "], Endpoint=[" + request.method + " " + request.path + "], "
                                                                                        "Post data=[" + json.dumps(request.form) + "], Args=[" + json.dumps(
                        request.args) + "]")
                # Assume it is a weekly event which does not repeat in multiple weeks
                till_date = event.begin.replace(days=+6).format('YYYY-MM-DD')

            # Monthly repeating events is not handled
            if frequency == "monthly":
                days_of_week = 0
            elif frequency == "daily":
                days_of_week = 127  # This value is not going to be used though
            elif frequency == "weekly":
                #Represented as a decimal value of binary value. Week starts on Monday.
                try:
                    p = re.compile('BYDAY=[^;]*')
                    m = p.search(event._unused[0].value)
                    days_of_week_str = m.group().split("=")[1].lower()
                    days_of_week_list = days_of_week_str.split(",")
                except:
                    # Get the day of the week of the start date of the event
                    day_of_week = event.begin.format("ddd")[:2].lower() # Convert to 2 letter format from 3 letter format
                    days_of_week_list = [day_of_week]

                days_of_week = get_days_of_week(days_of_week_list)
            else:
                app.logger.error(
                    "Unknown frequency [" + frequency + "] - [" + event.name + "]. Message=[" + json.dumps(
                        data) + "], Endpoint=[" + request.method + " " + request.path + "], Post data=[" + json.dumps(request.form) + "], Args=[" + json.dumps(
                        request.args) + "]")
                days_of_week = 0


        cur.execute("insert into events(user_id, is_active, course_id, name, start_time, end_time, frequency, from_date, till_date, days_of_week, date_created, date_updated) "
                         "values(%s, 1, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())", (user_id, course_id, event.name, start_time, end_time, frequency, from_date, till_date, days_of_week))

    data = {'malformed_events_list': malformed_events_list}

    return ("success", json.dumps(data))


@app.route('/', methods=['POST', 'GET'])
def main():
    if request.method == "GET":
        return render_template('index.html')
    else:
        try:
            (status, data) = input_ics_file()
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
        (status, data) = create_or_update_user(request.form['api_token'])
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


@app.route('/get_event_data', methods=['GET'])
def get_event_data():
    cur = create_db_connection()

    cur.execute("select id from users where api_token = %s order by id desc limit 1", [api_token])
    rv = cur.fetchall()

    return jsonify(status=status, data=data)

if __name__ == "__main__":
    app.run(debug=True)
