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
    'activities-steps-intraday':
    'https://api.fitbit.com/1/user/-/activities/steps/date/DATE/1d/1min.json',
    'activities-calories-intraday':
    'https://api.fitbit.com/1/user/-/activities/calories/date/DATE/1d/1min.json',
    'activities-distance-intraday':
    'https://api.fitbit.com/1/user/-/activities/distance/date/DATE/1d/1min.json',
    'activities-floors-intraday':
    'https://api.fitbit.com/1/user/-/activities/floors/date/DATE/1d/1min.json',
    'activities-elevation-intraday':
    'https://api.fitbit.com/1/user/-/activities/elevation/date/DATE/1d/1min.json'
}


@shared_task
def update_fitbit(oh_id):
    oh_member = OpenHumansMember.objects.get(oh_id=oh_id)
    if not hasattr(oh_member, 'fitbituser'):
        print('no fitbit user authorized yet!')
        return
    else:
        fb_user = oh_member.fitbituser
        fitbit_data, old_file_id, month = get_existing_fitbit(
                                                oh_member=oh_member)
        headers = {
            'Authorization': "Bearer %s" % fb_user.get_access_token()}
        if 'user' not in fitbit_data.keys():
            print('get user profile')
            response = requests.get(
                'https://api.fitbit.com/1/user/-/profile.json',
                headers=headers)
            print(response.json())
            fitbit_data['user'] = response.json()['user']
            print('got fitbit userprofile')
        update_endpoints(oh_member, fitbit_data, headers, old_file_id, month)


def identify_start_data_fetch(fitbit_data, data_key, month):
    if data_key in fitbit_data.keys():
        if len(fitbit_data[data_key]) > 0:
            start_date = fitbit_data[data_key][-1]['date']
            del(fitbit_data[data_key][-1])
            return fitbit_data, start_date
        elif month:
            return fitbit_data, month + '-01'
    return fitbit_data, fitbit_data['user']['memberSince']
    #return fitbit_data, "2018-10-28" # THIS IS JUST FOR TESTING TO KEEP THE DATA MANAGEABLE!


def get_single_endpoint(url, start_date, header):
    url = url.replace('DATE', str(start_date))
    response = requests.get(url, headers=header)
    if response.status_code == 200:
        return response.json()
    else:
        raise ValueError("Rate Limit")


def update_endpoints(oh_member, fitbit_data, header, old_file_id, month):
    rollovers = 0
    try:
        for endpoint, url in FITBIT_ENDPOINTS.items():
            print('start processing {} endpoint'.format(endpoint))
            fitbit_data, start_date = identify_start_data_fetch(
                                            fitbit_data, endpoint, month)
            print('start date for {}: {}'.format(endpoint, start_date))
            start_date = datetime.datetime.strptime(
                            start_date,
                            '%Y-%m-%d').date()
            end_date = datetime.date.today()
            while start_date <= end_date:
                new_data = get_single_endpoint(url, start_date, header)
                try:
                    new_data = new_data[endpoint]
                except KeyError:
                    subj = (
                        'ACTION REQUIRED: Configuration error in Fitbit'
                        'Intraday / Open Humans')
                    body = (
                        'Thanks for trying to use our Fitbit Intraday retrieval app!\n\n'
                        'It seems your app in Fitbit was misconfigured.\n'
                        'Did you remember to select "Personal" rather than "Server"?\n\n'
                        'Go here to return to our Setup instructions:\n'
                        'https://oh-fitbit-intraday.herokuapp.com/setup/'
                    )
                    oh_member.message(subject=subj, message=body)
                    return
                new_data['date'] = str(start_date)
                if endpoint in fitbit_data.keys():
                    fitbit_data[endpoint].append(new_data)
                else:
                    fitbit_data[endpoint] = [new_data]
                next_date = start_date + datetime.timedelta(days=1)
                if str(next_date)[:7] != str(start_date)[:7]:
                    # rolling over to the next month!
                    rollovers += 1
                    break
                else:
                    start_date = next_date
            print('finished updating {}'.format(endpoint))
    except ValueError:
        print('encountered rate limit for fitbit!')
        update_fitbit.apply_async(args=[oh_member.oh_id, ], countdown=3600)
        print('queued updates for post-api limit.')
        print('will now enter finally block to update data!')
    finally:
        with tempfile.TemporaryFile() as f:
            js = json.dumps(fitbit_data)
            js = str.encode(js)
            f.write(js)
            f.flush()
            f.seek(0)
            ohapi.api.upload_stream(
                f, "fitbit-intraday-{}.json".format(str(start_date)[:7]),
                metadata={
                    "description": "Intraday Fitbit Data",
                    "tags": [
                                "fitbit", 'intraday', 'heart rate',
                                'Fitbit Intraday', 'activity']
                    }, access_token=oh_member.get_access_token())
            if old_file_id:
                ohapi.api.delete_file(
                    file_id=old_file_id,
                    access_token=oh_member.get_access_token())
        print('updated data for {}'.format(oh_member.oh_id))
        if rollovers == 6:
            # all endpoints rolled over, time to initialize a "new" file for
            # next month!
            print('rolled over for all endpoints, init new file')
            new_fitbit_data = {
                'user': fitbit_data['user']
            }
            new_month = str(start_date + datetime.timedelta(days=1))
            for key in FITBIT_ENDPOINTS:
                new_fitbit_data[key] = [{'date': str(new_month)}]
            with tempfile.TemporaryFile() as f:
                js = json.dumps(new_fitbit_data)
                js = str.encode(js)
                f.write(js)
                f.flush()
                f.seek(0)
                ohapi.api.upload_stream(
                    f, "fitbit-intraday-{}.json".format(str(new_month)[:7]),
                    metadata={
                        "description": "Intraday Fitbit Data",
                        "tags": [
                                    "fitbit", 'intraday', 'heart rate',
                                    'Fitbit Intraday', 'activity']
                        }, access_token=oh_member.get_access_token())
            update_fitbit.apply_async(args=[oh_member.oh_id, ])
            print('wrote empty file for next month')
            print('enqueue next month!')
