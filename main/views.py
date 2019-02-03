from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect, render
import base64
import requests
from openhumans.models import OpenHumansMember
from .models import FitbitUser
from .tasks import update_fitbit


def _fitbit_is_setup(request):
    """
    Return True if user is logged in and Fitbit is set up.
    """
    if request.user.is_authenticated:
        if hasattr(request.user.openhumansmember, 'fitbituser'):
            if request.user.openhumansmember.fitbituser.access_token:
                return True
    return False


def index(request):
    """
    Starting page for app.
    """
    if request.user.is_authenticated:
        if _fitbit_is_setup(request):
            return redirect('dashboard')
        return redirect('setup')

    auth_url = OpenHumansMember.get_auth_url()
    context = {'auth_url': auth_url}

    return render(request, 'main/index.html', context=context)


def setup(request):
    """
    Set up Fitbit connection with API keys.
    """
    if not request.user.is_authenticated:
        return redirect('index')

    context = {
        'fb_redirect_uri': (
            settings.OPENHUMANS_APP_BASE_URL + '/fitbit/authorized')
    }

    if hasattr(request.user.openhumansmember, 'fitbituser'):
        context['fitbituser'] = request.user.openhumansmember.fitbituser
        if not request.user.openhumansmember.fitbituser.access_token:
            fb_user = request.user.openhumansmember.fitbituser
            fb_auth_url = (
                'https://www.fitbit.com/oauth2/authorize?response_type=code'
                '&client_id='+fb_user.personal_client_id+'&scope'
                '=activity%20nutrition%20heartrate%20location'
                '%20nutrition%20profile%20settings%20sleep%20social%20weight'
                '&redirect_uri='+settings.OPENHUMANS_APP_BASE_URL+'/'
                'fitbit/authorized')
            context['fb_auth_url'] = fb_auth_url

    return render(request, 'main/setup.html', context=context)


def dashboard(request):
    """
    Show files/status dashboard for user that has completed setup.
    """
    context = {'data_files': request.user.openhumansmember.list_files()}
    return render(request, 'main/dashboard.html', context=context)


def about(request):
    """
    Share further details about the project.
    """
    return render(request, 'main/about.html')


def logout_user(request):
    """
    Logout user.
    """
    if request.method == 'POST':
        logout(request)
    redirect_url = settings.LOGOUT_REDIRECT_URL
    return redirect(redirect_url)


def create_fitbit(request):
    """
    Collect fitbit client id/secret.
    """
    if request.method == 'POST':
        if hasattr(request.user.openhumansmember, 'fitbituser'):
            fb_user = request.user.openhumansmember.fitbituser
        else:
            fb_user = FitbitUser()
        fb_user.oh_member = request.user.openhumansmember
        fb_user.personal_client_id = request.POST.get('client_id')
        fb_user.personal_client_secret = request.POST.get('client_secret')
        fb_user.access_token = ''
        fb_user.refresh_token = ''
        fb_user.save()
    return redirect('/')


def delete_fitbit(request):
    """
    Delete fitbit client id/secret.
    """
    if request.method == 'POST':
        fb = request.user.openhumansmember.fitbituser
        fb.delete()
        return redirect('/')


def complete_fitbit(request):
    """
    Complete OAuth2 set up with Fitbit authorization.
    """

    code = request.GET['code']

    # Create Base64 encoded string of clientid:clientsecret for the headers
    # https://dev.fitbit.com/build/reference/web-api/oauth2/#access-token-request
    fb_user = request.user.openhumansmember.fitbituser
    client_id = fb_user.personal_client_id
    client_secret = fb_user.personal_client_secret
    encode_fitbit_auth = str(client_id) + ":" + str(client_secret)
    b64header = base64.b64encode(
                    encode_fitbit_auth.encode("UTF-8")).decode("UTF-8")

    # Add the payload of code and grant_type. Construct headers
    payload = {
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri':  settings.OPENHUMANS_APP_BASE_URL+'/fitbit/authorized'
        }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Basic %s' % (b64header)}

    # Make request for access token
    r = requests.post(
            'https://api.fitbit.com/oauth2/token', payload, headers=headers)
    rjson = r.json()

    # Save the user as a FitbitMember and store tokens
    fb_user.user_id = rjson['user_id']
    fb_user.access_token = rjson['access_token']
    fb_user.refresh_token = rjson['refresh_token']
    fb_user.expires_in = rjson['expires_in']
    fb_user.scope = rjson['scope']
    fb_user.token_type = rjson['token_type']
    fb_user.save()

    # Start async processing and return user to dashboard
    update_fitbit.delay(fb_user.oh_member.oh_id)
    return redirect('dashboard')
