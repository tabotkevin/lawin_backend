#!/usr/bin/env python
import os
from app import create_app, db
from app.models import User

app = create_app('production')

if __name__ == '__main__':
    app.run()

