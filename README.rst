========================
Agda
========================

Agda is a portal that provides easy and secure access to bioinformatic calculation.


To setup this project follow these steps:

#. Create your working environment
#. Install Django
#. Install additional dependencies


Working Environment
===================

You have several options in setting up your working environment.  We recommend
using virtualenv to seperate the dependencies of your project from your system's
python environment.  If on Linux or Mac OS X, you can also use virtualenvwrapper to help manage multiple virtualenvs across different projects.

Virtualenv Only
---------------

First, make sure you are using virtualenv (http://www.virtualenv.org). Once
that's installed, create your virtualenv::

    $ virtualenv --distribute agda

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

For LDAP you will need
sudo apt-get install libldap2-dev python-dev libldap2-dev libsasl2-dev libssl-dev

Adding you local config settings as ENV
=======================================

In virtualenv file:: 

    $ ~/home/.virtualenv/agda-dev/bin/activate

add something like this.::

    export AGDA_SECRET_KEY='Cryptographically complex string.'
    
    # Database engine - sqllite or mysql or postgresql. Ex :- django.db.backends.mysql
    export AGDA_DB_ENGINE="mydb engine"
    
    # Database Name. Ex:- Agda
    export AGDA_DB_NAME='mydb name'
    
    # Database User. Ex:- Agda
    export AGDA_DB_USER='mydb user'
    
    # Database Password for the user. Ex:- agdaUser
    export AGDA_DB_PASS='mydb password'
    
    # Base url for agda. Ex:- On local, http://localhost:8080, on server, http://agda.nsc.liu:8080/
    export AGDA_URL_BASE=""
    
    # Mail from Agda for password reset or account creation. Ex:- Agda <agda@nsc.liu.se> 
    export AGDA_MAIL_FROM=""
    
    export AGDA_MAIL_WATCHERS=""
    export AGDA_CONFIRMATION_MAIL_SECRET=''
    
    # path for AGDA UTILS. Ex:-/home/user/fido_utils
    export AGDA_UTILS=""
    
    # path for GRIDMAPFILE_BASE. Ex:-/srv/agda/grid-mapfiles/
    export GRIDMAPFILE_BASE=""

    # Depending on the setting you want to run local for dev, production for production server
    export DJANGO_SETTINGS_MODULE=agda.settings.local
    
    #LDAP settings

    export AGDA_AUTH_LDAP_BIND_PASSWORD"
    export AGDA_AUTH_LDAP_SERVER_URI=
    export AGDA_AUTH_LDAP_BIND_DN=
      
    #For lazy persons
    cd /path/to/src/agda


There is also a export skel file you can use to copy to your bin/activate or copy to any other place and source from bin/activate or by hand. 
Please see to that the activate file is secured on a multi user machine. 


Set up DB
============

For now we are running mysql as db backend. 
Set it up as your system recommend. 
Add a db and add user and set password. 


Testing
=======

To run tests it's recommended to use the coverage tool and the
agda.settings.test settings. Like this:

coverage run mangage.py test --settings agda.settings.test


Acknowledgements
================

    - twocoops book. 
    - 

.. _contributors: https://github.com/twoscoops/django-twoscoops-project/blob/master/CONTRIBUTORS.txt
