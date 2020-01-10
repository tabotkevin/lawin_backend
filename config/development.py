import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, '../data-dev.sqlite')


DEBUG = True
IGNORE_AUTH = True
SECRET_KEY = 'top-secret!'
UPLOAD_FOLDER = os.path.join(basedir, '../app/static/images')
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + db_path
WHOOSH_INDEX_PATH = os.path.join(basedir, 'search.sqlite')
