#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from solar_radiation_model.solar_radiation_model import runner
from twython import Twython, TwythonError
import model.database as db
from grapher import draw
import time
from twitter_keys import APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET
import random
from StringIO import StringIO
import itertools


def twython(func):
    def func_wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except TwythonError as e:
            print e
    return func_wrapper


class Presenter(object):

    def __init__(self):
        self.twitter = Twython(
            APP_KEY,
            APP_SECRET,
            OAUTH_TOKEN,
            OAUTH_TOKEN_SECRET
        )

    def upload_media(self, image):
        with open(image, 'rb') as photo:
            result = StringIO(photo.read())
        return result

    def tweet(self, status, images):
        time.sleep(10)
        medias = map(lambda i: self.upload_media(i), images)
        params = {'status': status}
        if not images:
            self.twitter.update_status(status=status)
        else:
            params['media'] = medias[0]
            self.twitter.post('/statuses/update_with_media',
                              params=params)
        print status, len(status)

    @twython
    def solarenergy_showcase(self, cache):
        filename = draw(history, 'map.png')
        self.tweet('Imagen de la última media hora.', filename)

    def demonstrate(self):
        cache = db.open()
        self.solarenergy_showcase(cache)
        db.close(cache)


presenter = Presenter()
presenter.demonstrate()
