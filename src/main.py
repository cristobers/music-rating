import secrets, requests
from urllib.parse import urlencode
from cryptography.fernet import Fernet
from flask import Flask, render_template, current_app, url_for, flash, session, \
    request, abort, redirect 
from flask_login import current_user, LoginManager, UserMixin, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from config import app_setup, fer_key

app = Flask(__name__)
app = app_setup(app)
db = SQLAlchemy(app)
login = LoginManager(app)
login.login_view = 'index'

key = fer_key
fernet = Fernet(key)

# https://blog.miguelgrinberg.com/post/oauth-authentication-with-flask-in-2023

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False)
    access_token  = db.Column(db.LargeBinary, nullable=False)
    refresh_token = db.Column(db.LargeBinary, nullable=False)
    expr_time     = db.Column(db.Integer, nullable=False)

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/home")
def home():
    return render_template("home.html")

@app.route("/logout")
def logout():
    logout_user()
    flash("you've been logged out")
    return redirect(url_for("index"))

@app.route('/authorize/<provider>')
def oauth2_authorize(provider):
    user_not_anonymous()
     
    provider_data = current_app.config['OAUTH2_PROVIDERS'].get(provider)
    if provider_data is None:
        abort(404)
     
    session['oauth2_state'] = secrets.token_urlsafe(16)

    qs = urlencode({
        'client_id': provider_data['client_id'],
        'redirect_uri': url_for('oauth2_callback', provider=provider, _external=True),
        'response_type': 'code',
        'scope': ' '.join(provider_data['scopes']),
        'state': session['oauth2_state'],
    })
    #print(url_for("oauth2_callback", provider=provider, _external=True))

    # redirect the user to the OAuth2 provider authorization URL
    return redirect(provider_data['authorize_url'] + '?' + qs)

@app.route('/callback/<provider>')
def oauth2_callback(provider):
    user_not_anonymous()
    provider_data = current_app.config['OAUTH2_PROVIDERS'].get(provider)
    if provider_data is None:
        abort(404)

    # if there was an authentication error, flash the error messages and exit
    if 'error' in request.args:
        for k, v in request.args.items():
            if k.startswith('error'):
                flash(f'{k}: {v}')
        return redirect(url_for('index'))

    # make sure that the state parameter matches the one we created in the
    # authorization request
    if request.args['state'] != session.get('oauth2_state'):
        abort(401)

    # make sure that the authorization code is present
    if 'code' not in request.args:
        abort(401)

    # exchange the authorization code for an access token
    response_tokens = requests.post(provider_data['token_url'], data={
        'client_id': provider_data['client_id'],
        'client_secret': provider_data['client_secret'],
        'code': request.args['code'],
        'grant_type': 'authorization_code',
        'redirect_uri': url_for('oauth2_callback', provider=provider, _external=True),
    }, headers={'Accept': 'application/x-www-form-urlencoded'})
    if response_tokens.status_code != 200:
        abort(401)
    #print(response_tokens.text)
    oauth2_token = response_tokens.json().get('access_token')
    print(oauth2_token)
    if not oauth2_token:
        abort(401)

    # use the access token to get the user's information
    response = requests.get("https://discord.com/api/users/@me", headers={
        'Authorization': 'Bearer ' + oauth2_token,
        'Accept': 'application/json',
    })

    #response_json = response.json()

    if response.status_code != 200:
        abort(401)

    user_info = {
        "id":               response.json()["id"],
        "username":         response.json()["username"],
        "access_token":     response_tokens.json()["access_token"],
        "refresh_token":    response_tokens.json()["refresh_token"],
        "expr_time":        response_tokens.json()["expires_in"]
    }

    # find or create the user in the database
    user = db.session.scalar(db.select(User).where(User.username == user_info["username"]))
    if user is None:
        user = User(id=user_info["id"], 
                    username=user_info["username"],
                    access_token=store_token(user_info["access_token"]),
                    refresh_token=store_token(user_info["refresh_token"]),
                    expr_time=user_info["expr_time"]
        )
        db.session.add(user)
        db.session.commit()
    # log the user in
    login_user(user)
    return redirect(url_for('index'))
    
def store_token(token: str) -> bytes:
    return fernet.encrypt(str.encode(token))

def retrieve_token(token: bytes) -> str:
    return (fernet.decrypt(token)).decode()

def user_not_anonymous():
    if not current_user.is_anonymous:
        return redirect(url_for('index'))

with app.app_context():
    db.create_all()
