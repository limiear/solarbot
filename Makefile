PYPREFIX_PATH=/usr
PYTHONLIBS=PIP_DOWNLOAD_CACHE=.cache/pip LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/lib
PYTHONPATH=$(PYPREFIX_PATH)/bin/python
FIRST_EASYINSTALL=$(PYTHONLIBS) easy_install
PIP=pip
PYTHON=bin/python
EASYINSTALL=bin/easy_install
VIRTUALENV=virtualenv
SOURCE_ACTIVATE=$(PYTHONLIBS) . bin/activate; 
ENVIRON=export LC_ALL=$(LANG); 

unattended:
	@ (sudo ls 2>&1) >> tracking.log

ubuntu:
	@ sudo apt-get -y install zlibc libssl1.0.0 libbz2-dev libxslt1-dev libxml2-dev python-gevent python-virtualenv python-dev libfreetype6-dev libpng12-dev libzip-dev m4 curl libxslt1-dev libxml2-dev --fix-missing
	@ echo "[ assume       ] ubuntu distribution"

swapon:
	@ echo "[ creating     ] swap file of 512 MB"
	@ dd if=/dev/zero of=/swapfile bs=1k count=512k
	@ chown root:root /swapfile
	@ chmod 0600 /swapfile
	@ mkswap /swapfile
	@ swapon /swapfile

swapoff: bin/activate
	@ echo "[ destroing    ] swap file of 512 MB"
	@ swapoff /swapfile
	@ rm /swapfile

bin/activate: requirements.txt
	@ echo "[ using        ] $(PYTHONPATH)"
	@ echo "[ installing   ] $(VIRTUALENV)"
	@ (sudo $(FIRST_EASYINSTALL) virtualenv 2>&1) >> tracking.log
	@ echo "[ creating     ] $(VIRTUALENV) with no site packages"
	@ ($(PYTHONLIBS) $(VIRTUALENV) --python=$(PYTHONPATH) --no-site-packages . 2>&1) >> tracking.log
	@ echo "[ installing   ] $(PIP) inside $(VIRTUALENV)"
	@ ($(SOURCE_ACTIVATE) $(EASYINSTALL) pip 2>&1) >> tracking.log
	@ echo "[ installing   ] $(PIP) requirements"
	@ $(SOURCE_ACTIVATE) $(PIP) install --upgrade pip
	@ $(SOURCE_ACTIVATE) $(PIP) install --upgrade distribute
	@ $(SOURCE_ACTIVATE) $(PIP) install --no-cache-dir -e  .
	@ $(SOURCE_ACTIVATE) $(PIP) install --default-timeout=100 -r requirements.development.txt
	@ touch bin/activate

deploy: bin/activate
	@ echo "[ deployed     ] the system was completly deployed"

rpi-deploy: swapon deploy swapoff

show-version:
	@ $(SOURCE_ACTIVATE) $(PYTHON) --version

run:
	@ date
	@ $(ENVIRON) $(SOURCE_ACTIVATE) $(PYTHON) solarbot/bot.py

test:
	@ $(SOURCE_ACTIVATE) $(PYTHON) tests

test-coverage-travis-ci:
	@ $(SOURCE_ACTIVATE) coverage run --source='solarbot/' tests/__main__.py

test-coveralls:
	@ $(SOURCE_ACTIVATE) coveralls

test-coverage: test-coverage-travis-ci test-coveralls

shell:
	@ $(SOURCE_ACTIVATE) ipython

pypi-register: test
	@ echo "[ record       ] package to pypi servers"
	@ ($(SOURCE_ACTIVATE) $(PYTHON) setup.py register -r pypi 2>&1) >> tracking.log
	@ echo "[ registered   ] the new version was successfully registered"

pypi-upload: test
	@ echo "[ uploading    ] package to pypi servers"
	@ ($(SOURCE_ACTIVATE) $(PYTHON) setup.py sdist upload -r https://pypi.python.org/pypi 2>&1) >> tracking.log
	@ echo "[ uploaded     ] the new version was successfully uploaded"

pypitest-register: test
	@ echo "[ record       ] package to pypi servers"
	@ $(SOURCE_ACTIVATE) $(PYTHON) setup.py register -r testpypi
	@ echo "[ registered   ] the new version was successfully registered"

pypitest-upload: test
	@ echo "[ uploading    ] package to pypi servers"
	$(SOURCE_ACTIVATE) $(PYTHON) setup.py sdist upload -r https://testpypi.python.org/pypi
	@ echo "[ uploaded     ] the new version was successfully uploaded"

clean:
	@ echo "[ cleaning     ] remove deployment generated files that doesn't exists in the git repository"
	@ rm -rf pip-*.json local/ python-aspects* virtualenv* bin/ lib/ *.egg-info/ lib64 include/ build/ share Python-* .Python get-pip.py tracking.log subversion
