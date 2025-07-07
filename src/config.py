import json, base64
from flask import Flask

PATH_TO_SECRETS = "/home/cris/music-rating/src/secrets.json"
assert PATH_TO_SECRETS != "", "Add the path to your secrets.json to PATH_TO_SECRETS."

with open(PATH_TO_SECRETS, "r") as f:
    f = json.loads(f.read())
    a_sk = f["app_secret_key"]
    c_id = f["client_id"]
    c_secret = f["client_secret"]
    fer_key  = f["fernet_key"]
    allowed_servers = f["allowed_servers"]

def app_setup(app):
    app.secret_key = a_sk
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
    app.config['OAUTH2_PROVIDERS'] = {
        'discord': {
            'client_id': c_id,
            'client_secret': c_secret,
            'authorize_url': 'https://discord.com/oauth2/authorize',
            'token_url': 'https://discord.com/api/oauth2/token',
            'userinfo': {
                'url': 'https://discord.com/oauth2/@me',
            },
            'scopes': ['identify', 'guilds']
        }
    }
    return app
