import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, '../data-test.sqlite')

DEBUG = False
TESTING = True
SECRET_KEY = 'top-secret!'
SERVER_NAME = 'example.com'
UPLOAD_FOLDER = os.path.join(basedir, '../app/static/images')
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path
WHOOSH_INDEX_PATH = os.path.join(basedir, 'search.sqlite')
