import json, base64
from flask import Flask

with open("/home/cris/music-rating/src/secrets.json", "r") as f:
    f = json.loads(f.read())
    a_sk = f["app_secret_key"]
    c_id = f["client_id"]
    c_secret = f["client_secret"]
    fer_key  = f["fernet_key"]

def app_setup(app):
    # TODO: hide these in the future bc this sucks
    app.secret_key = a_sk
    #app.config['FERNET_KEY'] = str.encode(fer_key)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
    app.config['OAUTH2_PROVIDERS'] = {
        'discord': {
            'client_id': "1385704476807135322",
            'client_secret': "HEoBopiDdEql4lAYvqLGRB1-U4NOrziu",
            'authorize_url': 'https://discord.com/oauth2/authorize',
            'token_url': 'https://discord.com/api/oauth2/token',
            'userinfo': {
                'url': 'https://discord.com/oauth2/@me',
                #'id': lambda n: n["id"]
            },
            'scopes': ['identify']
        }
    }
    return app
