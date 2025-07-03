# Music rating website

Allows users to login with Discord through Oauth2 and rate music that they've listened 
to.

## Oauth2 implementation

Thank you Miguel Grinberg for the implementation of Oauth2 used in this project which 
can be found at this blog post: 
https://blog.miguelgrinberg.com/post/oauth-authentication-with-flask-in-2023

## Setup

### Secrets

Make a `secrets.json` file within `src` which contains the following:

```json
{
    "app_secret_key": "secret key for flask",
    "client_id": "client id of discord oauth2",
    "client_secret": "client secret of discord oauth2" 
    "fernet_key": "a key for salting the db with fernet"
}
```
