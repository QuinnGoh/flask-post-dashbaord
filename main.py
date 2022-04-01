import datetime
import uuid
from flask import Flask, render_template, request, session, redirect
from google.cloud import datastore, storage

app = Flask(__name__, template_folder="templates")
datastore_client = datastore.Client()

CLOUD_STORAGE_BUCKET = 'uploaded-files-a1-parta'

# SECRET KEY FOR SESSION - SHOULD BE MOVED TO CONFIG FILES
app.secret_key = 'dhfgdufhgeh2837'


# CHECKS IF USER ALREADY IN DATABASE - RETURNS BOOLEAN TRUE / FALSE
def check_exist(_id) -> bool:
    complete_key = datastore_client.key("user", _id)
    outcome = False

    try:
        datastore_client.get(complete_key)

    except:

        outcome = False

    return outcome


# PUTS USER INTO DATASTORE
def register_user(_id, _user_name, _password, _profile_picture):
    complete_key = datastore_client.key("user", _id)
    entity = datastore.Entity(key=complete_key)
    entity.update({
        'user_name': _user_name,
        'password': _password,
        'id': _id,
        'user_blob_string': _profile_picture
    })
    # PUT OBJECT INTO DB
    datastore_client.put(entity)


# UPDATES / STORES POSTS IN GOOGLE DATASTORE FOR LATER REFERENCE
def store_post(_blob_string, _id, _message, _subject, _user_name, _key):
    entity = datastore.Entity(key=_key)

    entity.update({
        'message': _message,
        'blob_string': _blob_string,
        'subject': _subject,
        'user_name': _user_name,
        'user_id': _id,
        'dt': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        'user_blob_string': session['user_blob_string']
    })
    # PUT OBJECT INTO DB
    datastore_client.put(entity)


# CHECK IF USERNAME EXISTS IN DATASTORE
def check_exist_username(_username):
    query = datastore_client.query(kind="user")
    query.add_filter("user_name", "=", _username)

    try:
        return list(query.fetch())
    except:
        return False


# CHECK IF ID EXISTS IN DATASTORE
def check_exist_id(_id):
    key = datastore_client.key("user", _id)

    try:
        return datastore_client.get(key)
    except:
        return False


# REGISTER PAGE AND FUNCTIONALITY
@app.route('/register', methods=['GET', 'POST'])
def register():
    errors = []

    if request.method == 'POST':
        _id = request.form['id']
        _username = request.form['username']
        _password = request.form['password']

        if check_exist_id(_id):
            errors.append("ID")

        if check_exist_username(_username):
            errors.append("Username")

        if not errors:
            _profile_picture = upload(request.files.get('file'))

            register_user(_id, _username, _password, _profile_picture)

            return redirect('/login')
        else:
            return render_template('register.html', errors=errors)

    return render_template('register.html', errors=errors)


# REGISTER PAGE AND FUNCTIONALITY
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # RETRIEVE POSTS BASED ON ID IN SESSION
    post_list = retrieve_user_posts()
    # DYNAMICALLY DISPLAY POSTS FOR EDITING
    edit = 0
    # CHECK USER HAS LOGGED IN
    if not session.get('id'):
        return redirect('/login')

    # FORM TO CHANGE PASSWORD
    if request.method == 'POST' and request.form['submit_button'] == 'changePassword':
        error = change_password(request.form['old_password'], request.form['new_password'], session['id'])
        return render_template('profile.html', posts=post_list, user_blob_string=session['user_blob_string'],
                               user_name=session['username'], error=error)

    # FORM TO SELECT POST TO EDIT
    if request.method == 'POST' and request.form['submit_button'] != 'changePassword':
        post_key = get_post_key(request.form['submit_button'])
        selected_post = retrieve_post_from_id(post_key)

        # PASS POST ATTRIBUTES AS SESSION VALUES
        session['_edit_post_blob_string'] = selected_post['blob_string']
        session['_edit_post_message'] = selected_post['message']
        session['_edit_post_subject'] = selected_post['subject']
        session['selected_post_key'] = post_key

        return redirect('/profile-edit-post')

    return render_template('profile.html', posts=post_list, user_blob_string=session['user_blob_string'],
                           user_name=session['username'], edit=edit)


# EDIT POST PAGE FROM PROFILE
@app.route('/profile-edit-post', methods=['GET', 'POST'])
def profile_edit_post():
    if not session['selected_post_key']:
        return redirect('/profile')

    blob_string = session['_edit_post_blob_string']
    message = session['_edit_post_message']
    subject = session['_edit_post_subject']
    post_key = session['selected_post_key']

    # FORM TO EDIT POST
    if request.method == 'POST' and request.form['submit_button'] == 'EditPost':
        if request.files.get('file'):
            _blob_string = upload(request.files.get('file'))
        else:
            _blob_string = blob_string

        if request.form['message']:
            _message = request.form['message']
        else:
            _message = message

        if request.form['subject']:
            _subject = request.form['subject']
        else:
            _subject = subject

        store_post(_blob_string, session['id'], _message, _subject, session['username'],
                   datastore_client.key("post", get_post_key(post_key)))

        return redirect('/dashboard')

    return render_template('profile-edit-post.html', message=message, blob_string=blob_string, subject=subject,
                           user_blob_string=session['user_blob_string'], user_name=session['username'])


# DASHBOARD PAGE AND FUNCTIONALITY (CONTAINS POSTS)
@app.route('/dashboard', methods=['GET', 'POST'])
def home():
    # CHECK USER HAS LOGGED IN
    if not session.get('id'):
        return redirect('/login')
    # POST CONTENT FROM HTML FORM
    if request.method == 'POST':
        _message = request.form['message']
        _blob_string = upload(request.files.get('file'))
        _subject = request.form['subject']
        # POPULATES USER ATTRIBUTES BASED ON SESSION
        _user_name = session['username']
        _id = session['id']
        # CREATE DATASTORE KEY
        _key = datastore_client.key('post', uuid.uuid4().hex)
        # STORES THE POST IN THE DATASTORE
        store_post(_blob_string, _id, _message, _subject, _user_name, _key)
        return redirect('/dashboard')

    # RETRIEVE POSTS BASED ON ID IN SESSION
    post_list = retrieve_posts()

    return render_template('dashboard.html', posts=post_list, user_blob_string=session['user_blob_string'],
                           id=session['id'], user_name=session['username'])


# GET LAST 10 POSTS
def retrieve_posts():
    query = datastore_client.query(kind="post")
    query.order = ["-dt"]
    posts = list(query.fetch(limit=10))

    return posts


# STRIPS THE KEY PARSED BY DATASTORE TO DERIVE __KEY__ VALUE
def get_post_key(_key):
    staging = _key.replace("<Key('post', '", "")
    name = staging.replace("'), project=rmit-cloud-computing-2022-a1a>", "")

    return name


# RETRIEVES POSTS BASED ON POST ID FROM DATASTORE USING CLIENT.GET METHOD
def retrieve_post_from_id(post_key):
    try:
        key = datastore_client.key("post", post_key)
        return datastore_client.get(key)

    except:
        print("error with datastore retrieval")


# RETRIEVES POSTS BASED ON USER ID
def retrieve_user_posts():
    try:
        query = datastore_client.query(kind="post")
        query.add_filter("user_id", "=", session['id'])
        return list(query.fetch())

    except:
        print("error with datastore retrieval")


# CHANGE PASSWORD
def change_password(old_password, new_password, _id):
    complete_key = datastore_client.key("user", _id)

    try:
        existing_user = datastore_client.get(complete_key)
        existing_password = existing_user["password"]

        if existing_password == old_password and new_password != existing_password:
            entity = datastore.Entity(key=complete_key)
            entity.update({
                'user_name': existing_user["user_name"],
                'password': new_password,
                'id': existing_user["id"],
                'user_blob_string': existing_user["user_blob_string"]
            })
            print('Success')
            datastore_client.put(entity)
            error = 0

        else:
            print('Wrong password')
            error = 1

    except:
        print('Wrong password')
        error = 1

    return error


# UPLOAD BLOB TO CLOUD STORE AND PRODUCES STRING FOR DATASTORE ENTITY
def upload(file) -> str:
    if not file:
        return 'No file uploaded.', 400

    # Create a Cloud Storage client.
    gcs = storage.Client()

    # Get the bucket that the file will be uploaded to.
    bucket = gcs.get_bucket(CLOUD_STORAGE_BUCKET)

    # Create a new blob and upload the file's content.
    blob = bucket.blob(file.filename)

    blob.upload_from_string(
        file.read(),
        content_type=file.content_type
    )

    blob.make_public()

    # The public URL can be used to directly access the uploaded file via HTTP.
    return blob.public_url


# LOGIN PAGE AND FUNCTIONALITY
@app.route('/login', methods=['GET', 'POST'])
def login():

    error = False
    # CHECK USER HAS LOGGED IN
    if session.get('id') and session.get('username'):
        return redirect('/dashboard')
    if request.method == 'POST':
        _id = request.form['id']
        _password = request.form['password']
        # ASSIGN DATASTORE KEY BASED ON POST RESPONSE
        complete_key = datastore_client.key("user", _id)

        try:
            existing_user = datastore_client.get(complete_key)
            existing_password = existing_user["password"]
            existing_username = existing_user["user_name"]
            if existing_password == _password:
                session['username'] = existing_username
                session['id'] = _id
                session['user_blob_string'] = existing_user['user_blob_string']
                return redirect('/dashboard')

        except:
            error = True
            print('Not found')

    return render_template('login.html', error=error)


@app.route('/')
def index():
    return redirect('/dashboard')


# CLEARS SESSION AND RETURNS TO LOGIN PAGE
@app.route('/logout')
def logout():
    if session['username']:
        session.clear()

    return redirect('/login')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
