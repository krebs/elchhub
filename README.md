# ElchOS Hub
Find Linux distributions on all your ftp servers.

## Short Description
The intended Purpose of ElchOS is to share a lot of files on small nas-like
computers. The ElchHub is the central indexing service for all elch hosts.


## Architecture
The software is split into the `indexing webservice` for searching files and
the  `elch-manager` for performing the FTP crawl for new hosts.

## Usage

```
redis-server &
python elch-manager.py &
python wsgi.py

# a host registers itself at the elchHub:
curl localhost:5000/api/ping -H "Content-Type: application/json" -X POST -d '{"IP":"10.42.22.173","PORT":"2121"}'
```
## Hardware
Right now elchOS uses the **Seagate GoFlex Net** but every NAS with an ftp and
a tiny bit of shell script can be used.

For the GoFlex Net source code please refer to https://github.com/krebscode/elchos
