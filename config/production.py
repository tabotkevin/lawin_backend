import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, '../data.sqlite')

DEBUG = True
SECRET_KEY = 'top-secret!'
UPLOAD_FOLDER = os.path.join(basedir, '../app/static/images')
USER_UPLOAD_FOLDER = os.path.join(basedir, '../app/static/images/users')
FEED_UPLOAD_FOLDER = os.path.join(basedir, '../app/static/images/feeds')
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + db_path
WHOOSH_INDEX_PATH = os.path.join(basedir, 'search.sqlite')
