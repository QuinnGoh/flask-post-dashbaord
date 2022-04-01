from google.cloud import ndb


class user(ndb.Model):
    username = ndb.StringProperty()
    password = ndb.StringProperty()
    id = ndb.StringProperty()
    profile_blob_string = ndb.StringProperty()


class post(ndb.Model):
    blob_string = ndb.StringProperty()
    user_Id = ndb.StringProperty()
    message = ndb.StringProperty()
    subject = ndb.StringProperty()
    date_time = ndb.DateTimeProperty()
    user_blob_string = ndb.StringProperty()
    username = ndb.StringProperty()