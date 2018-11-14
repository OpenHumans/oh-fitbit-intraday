from celery import shared_task
from openhumans.models import OpenHumansMember
from .helpers import get_existing_fitbit
import requests
import datetime
import tempfile
import ohapi
import json


FITBIT_ENDPOINTS = {
    'activities-heart-intraday':
    'https://api.fitbit.com/1/user/-/activities/heart/date/DATE/1d/1sec.json',
}


@shared_task
def update_fitbit(oh_id):
    oh_member = OpenHumansMember.objects.get(oh_id=oh_id)
    if not hasattr(oh_member, 'fitbituser'):
        print('no fitbit user authorized yet!')
        return
    else:
        fb_user = oh_member.fitbituser
        fitbit_data, old_file_id = get_existing_fitbit(oh_member=oh_member)
        headers = {
            'Authorization': "Bearer %s" % fb_user.get_access_token()}
        if 'user' not in fitbit_data.keys():
            print('get user profile')
            response = requests.get(
                'https://api.fitbit.com/1/user/-/profile.json',
                headers=headers)
            fitbit_data['user'] = response.json()['user']
            print('got fitbit userprofile')
        update_endpoints(oh_member, fitbit_data, headers, old_file_id)


def identify_start_data_fetch(fitbit_data, data_key):
    if data_key in fitbit_data.keys():
        if len(fitbit_data[data_key]) > 0:
            start_date = fitbit_data[data_key][-1]['date']
            del(fitbit_data[data_key][-1])
            return fitbit_data, start_date
    return fitbit_data, fitbit_data['user']['memberSince']


def get_single_endpoint(url, start_date, header):
    url = url.replace('DATE', str(start_date))
    response = requests.get(url, headers=header)
    if response.status_code == 200:
        return response.json()
    else:
        raise ValueError("Rate Limit")


def update_endpoints(oh_member, fitbit_data, header, old_file_id):
    try:
        for endpoint, url in FITBIT_ENDPOINTS.items():
            print('start processing {} endpoint'.format(endpoint))
            fitbit_data, start_date = identify_start_data_fetch(
                                            fitbit_data, endpoint)
            print('start date for {}: {}'.format(endpoint, start_date))
            start_date = datetime.datetime.strptime(
                            start_date,
                            '%Y-%m-%d').date()
            end_date = datetime.date.today()
            while start_date <= end_date:
                new_data = get_single_endpoint(url, start_date, header)
                new_data = new_data[endpoint]
                new_data['date'] = str(start_date)
                if endpoint in fitbit_data.keys():
                    fitbit_data[endpoint].append(new_data)
                else:
                    fitbit_data[endpoint] = [new_data]
                start_date = start_date + datetime.timedelta(days=1)
            print('finished updating {}'.format(endpoint))
    except ValueError:
        print('encountered rate limit for fitbit!')
        print('will now enter finally block to update data!')
    finally:
        with tempfile.TemporaryFile() as f:
            js = json.dumps(fitbit_data)
            js = str.encode(js)
            f.write(js)
            f.flush()
            f.seek(0)
            ohapi.api.upload_stream(
                f, "fitbit-intraday.json", metadata={
                    "description": "Intraday Fitbit Data",
                    "tags": [
                                "fitbit", 'intraday', 'heart rate',
                                'Fitbit Intraday', 'activity']
                    }, access_token=oh_member.get_access_token())
            ohapi.api.delete_file(
                file_id=old_file_id,
                access_token=oh_member.get_access_token())
        print('updated data for {}'.format(oh_member.oh_id))
