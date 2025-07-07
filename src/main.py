import secrets, requests
from urllib.parse import urlencode
from cryptography.fernet import Fernet
from flask import Flask, render_template, current_app, url_for, flash, session, \
    request, abort, redirect, Response
from flask_login import current_user, LoginManager, UserMixin, login_user, \
    logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, Sequence, desc
from config import app_setup, fer_key, allowed_servers

app = Flask(__name__)
app = app_setup(app)
db = SQLAlchemy(app)
login = LoginManager(app)
login.login_view = "index"

key = fer_key
fernet = Fernet(key)

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id            = db.Column(db.String, primary_key=True)
    username      = db.Column(db.String(64), nullable=False)
    access_token  = db.Column(db.LargeBinary, nullable=False)
    refresh_token = db.Column(db.LargeBinary, nullable=False)
    expr_time     = db.Column(db.Integer, nullable=False)

class Album(db.Model):
    __tablename__ = "albums"
    id     = db.Column(db.Integer, Sequence("album_id_seq"), primary_key=True)
    title  = db.Column(db.String(512), nullable=False)   # Title of album
    artist = db.Column(db.String(512), nullable=False)   # Artist name
    date   = db.Column(db.String(512), nullable=False)   # Date added

class Rating(db.Model):
    __tablename__ = "ratings"
    id           = db.Column(db.Integer, Sequence("rating_id_seq"), primary_key=True)
    album_id     = db.Column(db.Integer, db.ForeignKey("albums.id"), nullable=False)
    album_rater  = db.Column(db.String(512), db.ForeignKey("users.id"), nullable=False)
    rating_score = db.Column(db.Integer, nullable=False)

@login.user_loader
def load_user(id):
    return db.session.get(User, str(id))

@app.route("/")
def index():
    # Only gather albums if the user is authenticated.
    if not current_user.is_authenticated:
        return render_template("index.html")
    else:
        albums = Album.query.all()
        ratings = get_ordered_albums_and_ratings()
        return render_template("index.html", albums=albums, ratings=ratings)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/user/<user_id>")
@login_required
def see_user_ratings(user_id, methods=["GET"]):
    username_given = False
    if len(user_id) <= 18 and not user_id.isdigit():
        username_given = True
        user_id = db.session.execute(
                db.select(User).where(
                    User.username == user_id
                )).one_or_none()
        if user_id == None:
            return "No user found with this username.", 400
        username = user_id[0].username
        user_id = user_id[0].id

    ratings = db.session.execute(
        db.select(Rating, Album).join(
            Album, Rating.album_id == Album.id
        ).where(and_(
            Rating.album_rater == user_id
        )).order_by(desc(Rating.rating_score))
    ).all()

    if ratings == []:
        return "User doesn't have any ratings.", 400
    else:
        if username_given:
            return render_template("ratings.html", ratings=ratings, user_id=username)
        else:
            return render_template("ratings.html", ratings=ratings, user_id=user_id)

@app.route("/rate_album", methods=["POST"])
@login_required
def rate_an_album():
    if request.form == None:
        return "Request data was empty.", 400

    album, artist = request.form["album"].split("\\0")
    # Check that the album exists
    albums = db.session.execute(
                db.select(Album).where(and_(
                    Album.title  == album,
                    Album.artist == artist
                ))).one_or_none()

    if albums == None:
        # We didn't find the album
        return "Couldn't find requested album in database.", 404

    score_given = request.form["rating"]
    if score_given == "":
        # Score was empty
        abort(400)

    prev_rated_album = db.session.execute(
        db.select(Rating, Album).join(
            Album, Rating.album_id == Album.id
        ).where(and_(
            Album.title  == album,
            Album.artist == artist,
            Rating.album_rater == current_user.id
        ))
    ).one_or_none()

    if prev_rated_album == None:
        temp_rating = Rating(
            album_id     = albums[0].id,
            album_rater  = current_user.id,
            rating_score = score_given
        )
        db.session.add(temp_rating)
        db.session.commit()
        flash(f"Successfully rated {album} by {artist}")
        return redirect(url_for("index"))
    else:
        prev_rated_album_id = prev_rated_album[1].id
        db.session.execute(
            db.update(Rating)
            .where(and_(
                Rating.album_id == prev_rated_album_id,
                Rating.album_rater == current_user.id
            ))
            .values(rating_score=score_given)
        )
        db.session.commit()
        flash(f"Updated your score for {album} by {artist}")
        return redirect(url_for("index"))

@app.route("/authorize/<provider>")
def oauth2_authorize(provider):
    user_not_anonymous()
     
    provider_data = current_app.config["OAUTH2_PROVIDERS"].get(provider)
    if provider_data is None:
        abort(404)
     
    session["oauth2_state"] = secrets.token_urlsafe(16)

    qs = urlencode({
        "client_id": provider_data["client_id"],
        "redirect_uri": url_for("oauth2_callback", provider=provider, _external=True),
        "response_type": "code",
        "scope": " ".join(provider_data["scopes"]),
        "state": session["oauth2_state"],
    })

    # redirect the user to the OAuth2 provider authorization URL
    return redirect(provider_data["authorize_url"] + "?" + qs)

@app.route("/callback/<provider>")
def oauth2_callback(provider):
    user_not_anonymous()
    provider_data = current_app.config["OAUTH2_PROVIDERS"].get(provider)
    if provider_data is None:
        abort(404)

    # if there was an authentication error, flash the error messages and exit
    if "error" in request.args:
        for k, v in request.args.items():
            if k.startswith("error"):
                flash(f"{k}: {v}")
        return redirect(url_for("index"))

    # make sure that the state parameter matches the one we created in the
    # authorization request
    if request.args["state"] != session.get("oauth2_state"):
        abort(401)

    # make sure that the authorization code is present
    if "code" not in request.args:
        abort(401)

    # exchange the authorization code for an access token
    response_tokens = requests.post(provider_data["token_url"], data={
        "client_id": provider_data["client_id"],
        "client_secret": provider_data["client_secret"],
        "code": request.args["code"],
        "grant_type": "authorization_code",
        "redirect_uri": url_for("oauth2_callback", provider=provider, _external=True),
    }, headers={"Accept": "application/x-www-form-urlencoded"})
    if response_tokens.status_code != 200:
        abort(401)
    oauth2_token = response_tokens.json().get("access_token")
    if not oauth2_token:
        abort(401)

    if is_user_allowed(oauth2_token) == False:
        abort(401)

    # use the access token to get the user"s information
    response = requests.get("https://discord.com/api/users/@me", headers={
        "Authorization": "Bearer " + oauth2_token,
        "Accept": "application/json",
    })

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
    user = db.session.scalar(
               db.select(User).where(
                   User.id == user_info["id"]
               )
           )

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

def is_user_allowed(oauth2_token):
    response = requests.get("https://discord.com/api/users/@me/guilds", headers={
        "Authorization": "Bearer " + oauth2_token,
        "Accept": "application/json",
    })

    if response.status_code != 200:
        abort(400)

    for server in response.json():
        if server["id"] in allowed_servers:
            return True
    return False

def get_ordered_albums_and_ratings():
    return db.session.execute(
        db.select(Rating, Album).join(
            Album, Rating.album_id == Album.id
        ).where(and_(
            Rating.album_rater == current_user.id 
        )).order_by(desc(Rating.rating_score))
    ).all()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
