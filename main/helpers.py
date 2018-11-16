import requests
import tempfile
from django.conf import settings
from main.models import Data
import json


def compile_fitbit(oh_member):
    fb_user = oh_member.fitbituser
    json_out = {}
    headers = {'Authorization': "Bearer %s" % fb_user.get_access_token()}
    hr = requests.get(
        'https://api.fitbit.com/1/user/-/activities/heart/date/today/1d/1sec.json',
        headers=headers)
    json_out['heart_rate'] = hr.json()['activities-heart-intraday']['dataset'][-1]['value']
    activity = requests.get(
        'https://api.fitbit.com/1/user/-/activities/date/today.json',
        headers=headers)
    json_out['steps'] = activity.json()['summary']['steps']
    sleep = requests.get(
        'https://api.fitbit.com/1.2/user/-/sleep/date/today.json',
        headers=headers)
    json_out['hours_slept'] = round(
        sleep.json()['summary']['totalMinutesAsleep']/60, 2)
    data, _ = Data.objects.get_or_create(
                oh_member=oh_member,
                data_type='fitbit')
    data.data = json.dumps(json_out)
    data.save()


def get_existing_fitbit(oh_member):
    fitbit_files = {}
    for dfile in oh_member.list_files():
        if 'Fitbit Intraday' in dfile['metadata']['tags']:
            # get file here and read the json into memory
            fitbit_files[dfile['basename'][16:23]] = dfile
    print("----")
    print(fitbit_files)
    print("----")
    if fitbit_files:
        filenames = list(fitbit_files.keys())
        filenames.sort()
        print("----")
        print(fitbit_files)
        print("----")
        last_file = fitbit_files[filenames[-1]]
        tf_in = tempfile.NamedTemporaryFile(suffix='.json')
        tf_in.write(requests.get(last_file['download_url']).content)
        tf_in.flush()
        fitbit_data = json.load(open(tf_in.name))
        print("fetched existing data from OH")
        # print(fitbit_data)
        return fitbit_data, last_file['id']
    fitbit_data = {}
    return fitbit_data, None
