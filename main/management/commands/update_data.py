from django.core.management.base import BaseCommand
from openhumans.models import OpenHumansMember
from main import helpers
import requests
from main.tasks import update_fitbit


class Command(BaseCommand):
    help = 'Process so far unprocessed data sets'

    def handle(self, *args, **options):
        for oh_member in OpenHumansMember.objects.all():
            if hasattr(oh_member, 'fitbituser'):
                update_fitbit.delay(oh_member.oh_id)
