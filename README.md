solarbot
==========

[![Gitter](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/limiear/solarbot?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[![License](https://img.shields.io/pypi/l/solarbot.svg)](https://raw.githubusercontent.com/limiear/solarbot/master/LICENSE) [![Downloads](https://img.shields.io/pypi/dm/solarbot.svg)](https://pypi.python.org/pypi/solarbot/) [![Build Status](https://travis-ci.org/limiear/solarbot.svg?branch=master)](https://travis-ci.org/limiear/solarbot) [![Coverage Status](https://coveralls.io/repos/limiear/solarbot/badge.png)](https://coveralls.io/r/limiear/solarbot) [![Code Health](https://landscape.io/github/limiear/solarbot/master/landscape.png)](https://landscape.io/github/limiear/solarbot/master) [![PyPI version](https://badge.fury.io/py/solarbot.svg)](http://badge.fury.io/py/solarbot)
[![Stories in Ready](https://badge.waffle.io/limiear/solarbot.png?label=ready&title=Ready)](https://waffle.io/limiear/solarbot)

Feed twitter with the Pergamino radiation map using the GERSolar estimation model running inside raspbian.

Requirements
------------

If you want to deploy this repository with the default settings, on any GNU/Linux or OSX system you just need to execute the next bash command to setting up all the requirements (GNUMakefile should have been installed to this point).

	$ make virtualenv deploy

On Ubuntu Desktop there are some other libraries not installed by default (zlibc curl libssl1.0.0 libbz2-dev libxslt-dev libxml-dev) which may need to be installed to use these library. Use the next command to automate the installation of the additional C libraries:

    $ make ubuntu virtualenv deploy


Configuration
-------------

To configure the bot fill the [**config.json**](https://github.com/limiear/solarbot/blob/master/config.json) file with your [NOAA CLASS account](http://www.nsof.class.noaa.gov/), [twitter app account](https://apps.twitter.com/), and a list of places contained inside the images of your suscription. The format of each place should be: 

    "name of the place": [lat, lon],


About
-----

This software is developed by [LIMIE](http://limiear.github.io/) and [GERSolar](http://www.gersol.unlu.edu.ar). You can contact us to <limiear.dev@gmail.com>.
