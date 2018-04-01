#!/bin/bash
# Very rudimentary start script
# Ideally, should use a uWSGI Configuration File and start it as daemon
cd ~/toggl-tartan
/home/nij/python_environments/tt/bin/uwsgi -s /tmp/tt.sock --manage-script-name --mount /=tt:app --virtualenv /home/nij/python_environments/tt >> ~/toggl-tartan/app.log 2>&1
