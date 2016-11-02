import requests, ftputil, ftplib, os, pprint, threading, time, random
import logging as log

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
                        print(name.decode('utf-8'))
                        if not ftp.path.isfile(name):
                                self.content_list.append({
                                        "type": "folder",
                                        "path": current_path,
                                        "name": name
                                })
                                try:
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

        def crawl(self):
                self.crawl_directory(self.ftp, self.ftp.curdir)
                return self.content_list

        def __init__(self, HOST, PORT ):
                self.HOST = HOST
                self.PORT = PORT
                self.ftp = ftputil.FTPHost(HOST, "anonymous", "", port=PORT, session_factory=self.MyFTPSession)
                self.content_list = []
