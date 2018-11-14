from celery import shared_task
from openhumans.models import OpenHumansMember
from .helpers import get_existing_fitbit
import requests


@shared_task
def update_fitbit(oh_id):
    oh_member = OpenHumansMember.objects.get(oh_id=oh_id)
    if not hasattr(oh_member, 'fitbituser'):
        return
    else:
        fb_user = oh_member.fitbituser
        fitbit_data = get_existing_fitbit(oh_member=oh_member)
        if 'user' not in fitbit_data.keys():
            print('get user profile')
            headers = {
                'Authorization': "Bearer %s" % fb_user.get_access_token()}
            response = requests.get(
                'https://api.fitbit.com/1/user/-/profile.json',
                headers=headers)
            fitbit_data['user'] = response.json()['user']
            print(fitbit_data)
