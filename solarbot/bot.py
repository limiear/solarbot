#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from models import JobDescription
from models.runner import goes
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
import pytz
import urllib
import matplotlib.pyplot as plt

short = (lambda f, start=2, end=-2:
                  ".".join((f.split('/')[-1]).split('.')[start:end]))
get_datetime = lambda f: datetime.strptime(short(f, 1), '%Y.%j.%H%M%S')
gmt = pytz.timezone('GMT')
local = pytz.timezone('America/Argentina/Buenos_Aires')
localize = lambda dt: (gmt.localize(dt)).astimezone(local)

def twython(func):
    def func_wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except TwythonError as e:
            print e
    return func_wrapper


def is_a_broked_file(filename):
    try:
        with nc.loader(filename) as root:
            data = nc.getvar(root, 'data')
            data[:]
        return False
    except Exception:
        return True


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
        self.tags = ['raspberrypi', 'noaa', 'goes', 'satellite',
                     'solarradiation', 'python', 'argentina',
                     'heliosat2']

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
        print status, len(status), screen_name
        self.twitter.send_direct_message(screen_name=screen_name, text=status)

    def indexes(self, lat, lon, place):
        diff = np.sqrt((lat - place[0]) ** 2 + (lon - place[1]) ** 2)
        return diff==diff.min()

    def graph_important_point(self, places):
        with nc.loader('data_new/*.nc') as root:
            lat, lon = nc.getvar(root, 'lat'), nc.getvar(root, 'lon')
            data = np.zeros(lat.shape[1:])
            for place in places.items():
                data[self.indexes(lat[0], lon[0], place[1])] = 1
            y, x = lat.shape[1:]
            plt.figure(figsize=(x/20, y/20))
            img = plt.imshow(data)
            img.set_clim(0, data.max())
            plt.title('inta')
            plt.colorbar()
            plt.axis('off')
            plt.savefig('location.png', bbox_inches=0)

    def get_area(self, lat, lon, places):
        to_string = lambda refs: '|'.join(map(lambda s: ','.join(s),
                                              refs))
        refs = [[str(lat[0, y, x]), str(lon[0, y, x])]
                for x in [0, -1] for y in [0, -1]]
        refs[2], refs[3] = refs[3], refs[2]
        refs.append(refs[0])
        refs_str = to_string(refs)
        area_map = ("http://maps.googleapis.com/maps/api/staticmap?"
                    "center=%s&zoom=7&size=400x400&maptype=roadmap&"
                    "sensor=false&path=color:red|weight:5|"
                    "fillcolor:white|%s" % (to_string([refs[0]]), refs_str))
        self.graph_important_point(places)
        urllib.urlretrieve(area_map, 'area_map.png')
        print area_map
        return area_map

    def getlastradiation(self, filepattern, places):
        radiations = []
        with nc.loader('static.nc') as static:
            lat, lon = nc.getvar(static, 'lat')[:], nc.getvar(static, 'lon')[:]
            self.get_area(lat, lon, places)
            idxs = map(lambda (p, c): (p, self.indexes(lat[0], lon[0], c)),
                      places.items())
            shape = lat.shape[1:]
            inside = lambda i, d: 0 < np.where(i)[d][0] < shape[d]
            idxs = filter(lambda (p, i): inside(i, 0) and inside(i, 1), idxs)
            files = sorted(glob.glob(filepattern))
            with nc.loader(files[-1]) as root:
                data = nc.getvar(root, 'globalradiation')
                radiations = map(lambda (p, c): (p, [
                    float(data[0, :][c]),
                    float(data[0, :][c])]), idxs)
        return dict(radiations)

    @twython
    def solarenergy_showcase(self, cache):
        filepattern = 'product/estimated/goes13.*.BAND_01.nc'
        places = {
            'home': (-33.910528, -60.581059),
            'inta': (-33.944332, -60.568668),
            'campo': (-34.030531, -60.476578),
            'ernesto': (-33.459296, -61.041577),
        }
        radiations = self.getlastradiation(filepattern, places)
        dt = get_datetime(self.files[-1])
        dt_here = localize(dt)
        dt_str = str(dt_here).split(' ')[-1]
        print dt_here, dt_str
        radiations = map(lambda t: "%s: %.2f" % (t[0], t[1][0]),
                         radiations.items())
        users = ['ecolell', 'gersolar']
        radiations = ', '.join(radiations)
        for u in users:
            self.say('[%s] Radiancias (W/[m².sr]): [%s]' %
                     (dt_str, radiations), u)
        filename = draw(filepattern, 'map.png', str(dt_here))
        self.tweet('Acabamos de estimar la irradiancia solar de las '
                   '%s para el area de Pergamino.' % dt_str,
                   ['area_map.png'])
        tag = random.choice(self.tags)
        self.tweet('[%s] Radiancia en W/[m².sr] a partir del '
                   'modelo de @gersolar. #%s' % (dt_str, tag),
                   filename)

    def remove_broked_files(self, files):
        size = lambda f: os.stat(f).st_size
        median_size = np.median(np.array(map(size, files)))
        broken = filter(lambda f: size(f) < median_size , files)
        print broken
        map(os.remove, broken)

    def demonstrate(self):
        diff = lambda dt, h: (dt - timedelta(hours=h))
        decimal = (lambda dt, h: diff(dt, h).hour +
                   diff(dt, h).minute / 60. + diff(dt, h).second / 3600.)
        should_download = lambda dt: decimal(dt, 4) >= 6 and decimal(dt, 4) <= 19
        filenames = []
        try:
            filenames = goes.download(USER, PASS, './%s' % self.directory,
                                      name=NAME,
                                      datetime_filter=should_download)
        except Exception, e:
            print 'Download skipped: ', e
        self.remove_broked_files(filenames)
        # self.remove_broked_files(glob.glob("temporal_cache/*.nc"))
        map(os.remove, glob.glob("temporal_cache/*.nc"))
        # self.remove_broked_files(glob.glob("product/estimated/*.nc"))
        map(os.remove, glob.glob("product/estimated/*.nc"))
        self.files = sorted(glob.glob('%s/goes13.*.BAND_01.nc' % self.directory))
        in_the_week = lambda f: get_datetime(f) >= datetime.utcnow() - timedelta(days=30)
        self.files = filter(in_the_week, self.files)
        name = lambda f: f.split('/')[-1]
        temps = glob.glob('temporal_cache/*.nc')
        last_temp = sorted(map(name, temps))[-1] if temps else ''
        last_data = name(self.files[-1]) if self.files else ''
        print last_temp, last_data
        if len(self.files) >= 28 and last_temp != last_data:
            begin = datetime.now()
            config = {
                'algorithm': 'heliosat',
                'data': '%s/*.nc' % self.directory,
                'temporal_cache': 'temporal_cache',
                'product': 'product/estimated'
            }
            job = JobDescription(**config)
            job.run()
            end = datetime.now()
            print 'Elapsed time %.2f seconds.' % (end - begin).total_seconds()
            cache = db.open()
            self.solarenergy_showcase(cache)
            db.close(cache)


if __name__ == '__main__':
    presenter = Presenter()
    presenter.demonstrate()
