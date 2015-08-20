#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from models import JobDescription
from models.runner import goes
from populartwitterbot import Bot
from grapher import draw
import time
import random
from StringIO import StringIO
from netcdf import netcdf as nc
import numpy as np
import os
import glob
import pytz
import urllib
import matplotlib.pyplot as plt
import json
import logging
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


short = (lambda f, start=2, end=-2:
                  ".".join((f.split('/')[-1]).split('.')[start:end]))
get_datetime = lambda f: datetime.strptime(short(f, 1), '%Y.%j.%H%M%S')
gmt = pytz.timezone('GMT')
local = pytz.timezone('America/Argentina/Buenos_Aires')
localize = lambda dt: (gmt.localize(dt)).astimezone(local)


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
        self.logger = logging.getLogger("solarbot")
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
            "log_solarbot.out", maxBytes=20, backupCount=5)
        self.logger.addHandler(handler)
        if 'CONFIG' in os.environ:
            CONFIG = os.environ['CONFIG']
        else:
            with open('config.json') as f:
                CONFIG = f.read()
        self.config = json.loads(CONFIG)
        self.twitter = Bot(self.config.items()[0])
        config = self.config['solarbot']
        self.noaaclass = config['noaaclass']
        self.job = config['job']
        self.places = config['places']
        if not os.path.exists(self.noaaclass['folder']):
            os.makedirs(self.noaaclass['folder'])
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
        self.logger.info("%s (%s)" % (status, len(status)))

    def say(self, status, screen_name):
        self.twitter.send_direct_message(screen_name=screen_name, text=status)
        self.logger.info("%s (%s) [%s]" % (status, len(status), screen_name))

    def indexes(self, lat, lon, place):
        diff = np.sqrt((lat - place[0]) ** 2 + (lon - place[1]) ** 2)
        return diff==diff.min()

    def graph_important_point(self, places):
        with nc.loader(self.job['data']) as root:
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
        self.logger.info(area_map)
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
            with nc.loader(filepattern) as root:
                data = nc.getvar(root, 'globalradiation')
                radiations = map(lambda (p, c): (p, [
                    float(data[-1][c]),
                    float(data[-1][c])]), idxs)
        return dict(radiations)

    def solarenergy_showcase(self):
        filepattern = '%s/goes13.*.BAND_01.nc' % self.job['product']
        radiations = self.getlastradiation(filepattern, self.places)
        dt = get_datetime(self.files[-1])
        dt_here = localize(dt)
        dt_str = str(dt_here).split(' ')[-1]
        self.logger.info(dt_str)
        radiations = map(lambda t: "%s: %.2f" % (t[0], t[1][0]),
                         radiations.items())
        users = ['ecolell', 'gersolar']
        radiations = ', '.join(radiations)
        for u in users:
            self.say('[%s] Irradiancias (W/[m².sr]): [%s]' %
                     (dt_str, radiations), u)
        filename = draw(filepattern, 'map.png', str(dt_here))
        self.tweet('Acabamos de estimar la irradiancia solar de las '
                   '%s para el area de Pergamino.' % dt_str,
                   ['area_map.png'])
        tag = random.choice(self.tags)
        self.tweet('[%s] Irradiancia en W/(m².sr) a partir del '
                   'modelo de @gersolar. #%s' % (dt_str, tag),
                   filename)

    def remove_broked_files(self, files):
        size = lambda f: os.stat(f).st_size
        median_size = np.median(np.array(map(size, files)))
        broken = filter(lambda f: size(f) < median_size , files)
        self.logger.info(str(broken))
        map(os.remove, broken)

    def demonstrate(self):
        diff = lambda dt, h: (dt - timedelta(hours=h))
        decimal = (lambda dt, h: diff(dt, h).hour +
                   diff(dt, h).minute / 60. + diff(dt, h).second / 3600.)
        should_download = lambda dt: decimal(dt, 4) >= 6 and decimal(dt, 4) <= 19
        filenames = []
        uptime = goes.noaaclass.next_up_datetime()
        if uptime < pytz.utc.localize(datetime.utcnow()):
            self.noaaclass["datetime_filter"] = should_download
            try:
                filenames = goes.download(**(self.noaaclass))
            except Exception, e:
                self.logger.info('Download skipped: %s' % (str(e)))
        else:
            self.tweet("The NOAA CLASS is down, the system will be back "
                       "at %s" % str(uptime))
        self.remove_broked_files(filenames)
        get_temporals = (lambda:
                         glob.glob('%s/*.nc' % self.job['temporal_cache']))
        map(os.remove, get_temporals())
        map(os.remove, glob.glob('%s/*.nc' % self.job['product']))
        self.files = sorted(glob.glob(self.job['data']))
        in_the_week = lambda f: get_datetime(f) >= datetime.utcnow() - timedelta(days=30)
        self.files = filter(in_the_week, self.files)
        name = lambda f: f.split('/')[-1]
        temps = get_temporals()
        last_temp = sorted(map(name, temps))[-1] if temps else ''
        last_data = name(self.files[-1]) if self.files else ''
        self.logger.info("%s %s" % (last_temp, last_data))
        if len(self.files) >= 28 and last_temp != last_data:
            begin = datetime.now()
            job = JobDescription(**(self.job))
            job.run()
            end = datetime.now()
            self.logger.info('Elapsed time %.2f seconds.' %
                            (end - begin).total_seconds())
            self.solarenergy_showcase()


if __name__ == '__main__':
    presenter = Presenter()
    presenter.demonstrate()
