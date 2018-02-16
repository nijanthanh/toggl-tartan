from ics import Calendar
import requests
import json

#fp = open('canvas.ics', 'rb')
fp = open('google-calendar.ics', 'rb')
data = fp.read()

c = Calendar(data.decode("utf-8"))

begin_date = ""

for event in c.events:
    print(event)


def create_task(api_token, description, project_id, start_time, duration):
    params = {}
    # {"time_entry":{"description":"Meeting with possible clients","tags":["toggltartan"],"duration":4800,"start":"2018-02-13T07:58:58.000Z","pid":94945801,"created_with":"toggltartan"}}
    params['description'] = description
    params['tags'] = '["toggl-tartan"]'
    params['duration'] = duration
    #params['start'] = "2018-02-13T07:58:58.000Z"
    params['start'] = start_time
    params['pid'] = project_id
    params['created_with'] = "toggl-tartan"

    dataDict = {}
    dataDict['time_entry'] = params
    data = json.dumps(dataDict)

    headers = {'Content-Type': 'application/json'}
    r = requests.post("https://www.toggl.com/api/v8/time_entries", headers=headers, auth=(api_token, 'api_token'), data=data)
    #x = r.json()
    print(r.text)

def get_project_id():
    return 1

begin_date_time = event.begin.format('YYYY-MM-DDTHH:mm:ss.000') + "Z"
create_task("XXXX", "XYZ", 94945801, begin_date_time, 4800)