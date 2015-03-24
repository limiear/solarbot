#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from models.runner import heliosat, goes
from twython import Twython, TwythonError
import model.database as db
from grapher import draw
import time
from twitter_keys import APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET
from noaa_keys import USER, PASS, NAME
import random
from StringIO import StringIO
from netcdf import netcdf as nc
import numpy as np
import os
import glob
import json
import pytz

short = (lambda f, start=2, end=-2:
                  ".".join((f.split('/')[-1]).split('.')[start:end]))
get_datetime = lambda f: datetime.strptime(short(f, 1), '%Y.%j.%H%M%S')

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
        self.directory = 'data_new'
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

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

    def say(self, status, screen_name):
        self.twitter.send_direct_message(screen_name=screen_name, text=status)

    def indexes(self, lat, lon, place):
        diff = np.sqrt((lat - place[0]) ** 2 + (lon - place[1]) ** 2)
        return diff==diff.min()

    def get_area(self, lat, lon):
        to_string = lambda refs: '|'.join(map(lambda s: ','.join(s),
                                              refs))
        refs = [[str(lat[0, y, x]), str(lon[0, y, x])]
                for x in [0, -1] for y in [0, -1]]
        refs[2], refs[3] = refs[3], refs[2]
        refs.append(refs[0])
        refs_str = to_string(refs)
        return ("http://maps.googleapis.com/maps/api/staticmap?"
                "center=%s&zoom=8&size=600x600&maptype=satellite&sensor=false&"
                "path=color:red|weight:5|"
                "fillcolor:white|%s" % (to_string([refs[0]]), refs_str))

    def getlastradiation(self, filepattern, places):
        radiations = []
        with nc.loader('static.nc') as static:
            lat, lon = nc.getvar(static, 'lat')[:], nc.getvar(static, 'lon')[:]
            self.get_area(lat, lon)
            idxs = map(lambda (p, c): (p, self.indexes(lat[0], lon[0], c)),
                      places.items())
            shape = lat.shape[1:]
            inside = lambda i, d: 0 < np.where(i)[d][0] < shape[d]
            idxs = filter(lambda (p, i): inside(i, 0) and inside(i, 1), idxs)
            with nc.loader(filepattern) as root:
                data = nc.getvar(root, 'globalradiation')
                radiations = map(lambda (p, c): (p, [
                    float(data[-1][c]),
                    float(data[-1][c])]), idxs)
        return dict(radiations)

    @twython
    def solarenergy_showcase(self, cache):
        filepattern = 'temporal_cache/goes13.*.BAND_01.nc'
        places = {
            'home': (-33.910528, -60.581059),
            'inta': (-33.944332, -60.568668),
            'campo': (-34.030531, -60.476578),
            'ernesto': (-33.459296, -61.041577),
        }
        radiations = self.getlastradiation(filepattern, places)
        gmt = pytz.timezone('GMT')
        local = pytz.timezone('America/Argentina/Buenos_Aires')
        dt = gmt.localize(get_datetime(self.files[-1]))
        dt_here = dt.astimezone(local)
        dt_str = str(dt_here)
        radiations = map(lambda t: t[0] + ': ' + str(t[1][0]), radiations.items())
        for r in radiations:
            self.say('[%s] Radiación de %s' % (dt_str, r),
                     'ecolell')
        filename = draw(filepattern, 'map.png')
        self.tweet('Radiación de %s.' % dt_str, filename)

    def demonstrate(self):
        diff = lambda dt, h: (dt - timedelta(hours=h))
        decimal = lambda dt, h: diff(dt, h).hour + diff(dt, h).minute / 60. + diff(dt, h).second / 3600.
        should_download = lambda dt: decimal(dt, 4) >= 6 and decimal(dt, 4) <= 18
        filenames = goes.download(USER, PASS, './%s' % self.directory,
                                  name=NAME,
                                  datetime_filter=should_download)
        self.files = glob.glob('%s/goes13.*.BAND_01.nc' % self.directory)
        sorted(self.files)
        if len(self.files) >= 28:
            begin = datetime.now()
            heliosat.workwith('%s/goes13.*.BAND_01.nc' % self.directory)
            end = datetime.now()
            print 'Elapsed time %.2f seconds.' % (end - begin).total_seconds()
            cache = db.open()
            self.solarenergy_showcase(cache)
            db.close(cache)


presenter = Presenter()
presenter.demonstrate()
