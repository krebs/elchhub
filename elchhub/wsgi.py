#!/usr/bin/python
# -*- coding: utf-8 -*-

from elchhub.elchos import app

app.config['PROPAGATE_EXCEPTIONS'] = True

if __name__ == '__main__':
    app.run(debug=False)
