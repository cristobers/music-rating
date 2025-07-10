import json, base64
from flask import Flask

PATH_TO_SECRETS = "src/secrets.json"

with open(PATH_TO_SECRETS, "r") as f:
    f = json.loads(f.read())
    admins = f["admins"]
    a_sk = f["app_secret_key"]
    c_id = f["client_id"]
    c_secret = f["client_secret"]
    fer_key  = f["fernet_key"]
    allowed_servers = f["allowed_servers"]

def app_setup(app):
    app.secret_key = a_sk
    app.jinja_options["autoescape"] = True
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
