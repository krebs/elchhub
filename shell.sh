#!/bin/sh
nix-shell -p python2Packages.requests2 python2Packages.flask \
  python2Packages.gunicorn python2Packages.gevent python2Packages.ftputil \
  python2Packages.redis \
  /nix/store/faw12krm5ymxyhd2mzc3c61v182ih0j5-python2.7-nltk-3.2.1 \
  python2Packages.sqlite3
