from glob import glob
import pytz
from datetime import datetime


short = (lambda f, start=2, end=-2:
                  ".".join((f.split('/')[-1]).split('.')[start:end]))
get_datetime = lambda f: datetime.strptime(short(f, 1), '%Y.%j.%H%M%S')
files = glob('data_new/*.nc')
sorted(files)
dt = get_datetime(files[-1])
gmt = pytz.timezone('GMT')
local = pytz.timezone('America/Argentina/Buenos_Aires')
dt = gmt.localize(dt)
dt_here = dt.astimezone(local)
dt_str = str(dt_here).split(' ')[-1]
print dt_here
print dt_str
