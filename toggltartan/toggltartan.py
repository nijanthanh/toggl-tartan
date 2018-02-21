import os
import json

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


def input_ics_file():
    calendar_file = os.path.join(app.root_path, 'scripts/canvas.ics')

    with open(calendar_file) as f:
        calendar_data = f.read()

    if not calendar_data:
        raise (TogglTartanError("Oops! Could not read data from the .ics file"))
        return ("error", "")

    c = Calendar(calendar_data)

    cur = mysql.connection.cursor()

    api_token = request.form['api_token']
    res = create_or_update_user(api_token)

    data = json.loads(res[1]);
    user_id = data['user_id']

    for event in c.events:
        print(event)
        # cur.execute('''UPDATE USERS''')
        # rv = cur.fetchall()

    return ("success", "")


@app.route('/', methods=['POST', 'GET'])
def main():
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


    # return render_template('index.html')


@app.route('/submit_api_token')
def submit_api_token(name=None):
    # Make request to https://www.toggl.com/api/v8/me
    # If empty result, notify users. Else update users table.

    return render_template('hello.html', name=name)


if __name__ == "__main__":
    app.run(debug=True)
