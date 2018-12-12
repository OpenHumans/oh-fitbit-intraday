# Integrate Fitbit Intraday Access into Open Humans

Heavily WIP



## Local deployment

Follow the instructions [here](https://github.com/gedankenstuecke/oh_data_uploader/blob/master/INSTALL.md)

Additional steps required are below.

### Open Humans Project Redirect Url

Set the redirect url to `http://127.0.0.1:5000/openhumans/complete` when [creating your project on open humans](https://github.com/gedankenstuecke/oh_data_uploader#step-3-create-your-project-on-open-humans). When the project is live you'll need to change it to the heroku url.

### Env file

Make sure to set the following vars. The client id and secret is created [here](https://github.com/gedankenstuecke/oh_data_uploader#step-3-create-your-project-on-open-humans).

```
OPENHUMANS_CLIENT_ID=your_client_id
OPENHUMANS_CLIENT_SECRET=your_client_secret
OPENHUMANS_APP_BASE_URL=http://127.0.0.1:5000
```

### Redis

Before doing `heroku local`, need to have a redis instance running locally. 
One way to do that is:

```docker run --name some-redis -p 6379:6379 -d redis```


