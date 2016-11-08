import requests, ftputil, ftplib, os, pprint, threading, time, random
import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('elch-ftp-crawler')

class FTP_Crawler:
    class MyFTPSession(ftplib.FTP):
        def __init__(self, host, userid, password, port):
            """Act like ftplib.FTP's constructor but connect to another port."""
            ftplib.FTP.__init__(self)
            self.connect(host, port)
            self.login(userid, password)

    def crawl_directory(self, ftp, directory):
        if directory != ".": ftp.chdir(directory) #Decend into directory
        current_path = ftp.getcwd().strip("/") if directory != "." else ""
        names = ftp.listdir(ftp.curdir)

        for name in names:
            if not ftp.path.isfile(name):
                self.content_list.append({
                    "type": "folder",
                    "path": current_path,
                    "name": name
                    })
                try:
                    log.info("Crawling: {}".format(directory))
                    self.crawl_directory(ftp, name)
                except:
                    log.error("unable to crawl {}".format(directory))
            else:
                self.content_list.append({
                    "type": "file",
                    "size": ftp.stat(name).st_size,
                    "path": current_path,
                    "name": name
                    })

                ftp.chdir(ftp.pardir) #Go back to the parent directory

    def get_index(self,ftp):
        from io import BytesIO
        import os.path
        import lzma
        import re
        index_name = "index.xz"
        with ftp.open(index_name,"rb") as idx:
            uncompressed = lzma.open(idx,"rb")
            for l in uncompressed.readlines():
                l = l.decode('utf-8','ignore').strip("\n")
                size,typ,fullname = l.split(" ",maxsplit=2)
                fullname = re.sub(r'^./?','',fullname)
                if not fullname: continue # skip /
                path = os.path.dirname(fullname)
                name = os.path.basename(fullname)
                entry = {
                    # everything not a folder is a file (lol hardlinks & sockets)
                    "type": "folder" if typ == "d" else "file",
                    "size": size,
                    "path": path,
                    "name": name
                }
                log.debug(entry)
                self.content_list.append(entry)

    def crawl(self):
        try:
            log.info("Retrieving index.xz")
            self.get_index(self.ftp)
            log.info("Finished elchOS Index retrieval")
        except:
            log.warn("No ElchOS Index file,crawling manually")
            self.crawl_directory(self.ftp, self.ftp.curdir)

        return self.content_list

    def __init__(self, HOST, PORT ):
        self.HOST = HOST
        self.PORT = PORT
        self.ftp = ftputil.FTPHost(HOST, "anonymous", "", port=PORT, session_factory=self.MyFTPSession)
        self.content_list = []
