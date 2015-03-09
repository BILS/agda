========================
Requirements for getting Agda running on CentOS 6.5
========================

Run this to install required yum packages

$ sudo yum install python-virtualenv python-virtualenvwrapper cracklib-devel mysql-devel python-devel openldap-devel openssl-devel libgsasl-devel

Then, create your virtualenv with virtualenvwrapper and run this inside:

$ pip install -r requirements/local.txt

