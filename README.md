## RIFT Shard First web site

Sister project to [RIFT Firsts XML Parser](https://github.com/chennin/rift-xml-firsts-parser) which parses the shard firsts in to a database. This is the web page portion.

## Requirements

* Python 3.5
* Yattag
* A WSGI such as uwsgi

## Config

Copy `config.txt.dist` to `config.txt` and fill in all settings. `ZIPDIR` is the location of your downloaded Rift\_Discoveries\*.zip which should have been downloaded when you set up the firsts XML parser.

Also requires the database set up and filled in like in the firsts XML parser.

## Running

Serve index.py via WSGI. The specifics and the HTTPd (optional) setup is beyond the scope of this README, but I am successfully using NGINX to proxy to [uwsgi](https://uwsgi-docs.readthedocs.io/en/latest/Python.html). The following is the uwsgi command I am using:

    uwsgi --socket 127.0.0.1:3031 --need-plugin python3 --master --enable-threads --wsgi-file index.py

## Thanks

To Stuart Langridge for sorttable.js
