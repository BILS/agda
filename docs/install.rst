Install
=========


To use this project follow these steps:

#. Requirements
#. Create your working environment
#. Install Django
#. Install additional dependencies
#. Adding you local config settings as ENV
#. Set up DB

Requirements
============

* Computer
* A OS preferably a linux dist
* Python (you get this for free when you run linux :) )
* Git


Working Environment
===================

You have several options in setting up your working environment.  We recommend
using virtualenv to seperate the dependencies of your project from your system's
python environment.  If on Linux or Mac OS X, you can also use virtualenvwrapper to help manage multiple virtualenvs across different projects.

Virtualenv Only
---------------

First, make sure you are using virtualenv (http://www.virtualenv.org). Once
that's installed, create your virtualenv::

    $ virtualenv --distribute agda-dev

You will also need to ensure that the virtualenv has the project directory
added to the path. Adding the project directory will allow `django-admin.py` to
be able to change settings using the `--settings` flag.

Virtualenv with virtualenvwrapper
--------------------------

In Linux and Mac OSX, you can install virtualenvwrapper (http://virtualenvwrapper.readthedocs.org/en/latest/),
which will take care of managing your virtual environments and adding the
project path to the `site-directory` for you::

    $ mkdir agda
    $ mkvirtualenv -a agda agda-dev
    $ cd agda && add2virtualenv `pwd`

Installation of Dependencies
=============================

Depending on where you are installing dependencies:

In development::

    $ pip install -r requirements/local.txt

For production::

    $ pip install -r requirements.txt

*note: We install production requirements this way because many Platforms as a
Services expect a requirements.txt file in the root of projects.*


Adding you local config settings as ENV
=======================================

In virtualenv file::

    $ ~/home/.virtualenv/agda-dev/bin/activate

add something like this.::

    export AGDA_SECRET_KEY='Cryptographically complex string.'
    export AGDA_DB_USER='mydbuser'
    export AGDA_DB_PASS='my db password'

    #Depending on the setting you want to run local for dev, production for production server
    export DJANGO_SETTINGS_MODULE=agda.settings.local
    #For lazy persons
    cd /path/to/src/agda


There is also a export skel file you can use to copy to your bin/activate or copy to any other place and source from bin/activate or by hand.
Please see to that the activate file is secured on a multi user machine.


Set up DB
============

For now we are running mysql as db backend.
Set it up as your system recommend.
Add a db and add user and set password.

