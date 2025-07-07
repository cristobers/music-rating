# Music rating website

## Why this exists

Discord puts a hard limit on the amount of variables you can have on a single command, 
after trying to put as much information into a single command, we have reached the limit.
This Flask application was made to allow for more verbose rating of albums, without
having to worry about Discords imposed bot command limitations.

## Oauth2 implementation

Thank you Miguel Grinberg for the implementation of Oauth2 used in this project which 
can be found at this blog post: 
https://blog.miguelgrinberg.com/post/oauth-authentication-with-flask-in-2023

## Setup

### Secrets

Make a `secrets.json` file within `src` which contains the following:

```json
{
    "allowed_servers": ["array of discord server ids allowed to login"],
    "app_secret_key": "secret key for flask",
    "client_id": "client id of discord oauth2",
    "client_secret": "client secret of discord oauth2" 
    "fernet_key": "a key for salting the db with fernet"
}
```

Add the path to this file to `src/config.py` in the `PATH_TO_SECRETS` variable.
