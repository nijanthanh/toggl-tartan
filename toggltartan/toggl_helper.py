import requests
from toggltartan.toggl_tartan_error import *

def get_current_user_data(api_token):
    r = requests.get("https://www.toggl.com/api/v8/me", auth=(api_token, 'api_token'))

    if r.status_code != 200:
        raise (TogglTartanError("Invalid Toggl API token. Copy your Toggl API token from your <a href='https://www.toggl.com/app/profile'>Toggle profile page.</a>"))

    return r.json()