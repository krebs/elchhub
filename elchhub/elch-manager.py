#!/usr/bin/env python

from Crawler import FTP_Crawler
import redis

r = redis.StrictRedis(host='localhost', port=6379, db=0)
pubsub = r.pubsub()
r.config_set('notify-keyspace-events','KEA')
#pubsub.psubscribe('__keyspace@*__:expired')
#pubsub.psubscribe('*')
pubsub.subscribe('__keyevent@0__:expired')
pubsub.subscribe('new_node')
pubsub.subscribe('update_node')

def recreate_index():
    import re
    # cleanup index
    print("index cleanup")
    for k in r.scan_iter(match="search:index:*"):
        r.delete(k)
    for k in r.scan_iter(match="store:*"):
        # TODO tokenize with nltk instead of this
        # todo: remove stopwords
        print("index for {}".format(k))

        # add index for keywords in name:
        for token in filter(None,
                set(re.split("[\W_]",r.hget(k,"name").lower()))):
            # folders value more than files
            r.zadd("search:index:" + token,20 if r.hget(k,"type") == "folder" else 10,k)
        # add index for keywords in path

        pathlist = r.hget(k,"path").lower().split("/")
        for idx,directory in enumerate(reversed(pathlist)):
            for token in filter(None,set(re.split("[\W_]",directory))):
                # TODO: use 10 - (len()-index())  as increment to 
                score = 9 - idx if idx < 9 else 1
                r.zincrby("search:index:" + token,k,score)


for msg in pubsub.listen():
    print(msg)
    if msg['type'] == 'subscribe':continue
    node = msg['data']
    if msg['channel'] == 'update_node':
        print('extend ttl for {}'.format(node))
        r.expire("nodes:{}".format(node),300)
    if msg['channel'] == 'new_node':
        #Crawl this server
        print("Starting to crawl " + node)
        HOST,PORT = node.split(':')
        r.sadd("in-progress",node)
        crawler = FTP_Crawler(HOST, PORT)
        content_list = crawler.crawl()
        for item in content_list:
            from hashlib import sha256
            # path never has either leading or trailing slashes
            try:
                print("path: {}".format(item['path']))
                print("name: {}".format(item['name']))
            except: pass
            k = "store:{}:{}".format(node,
                                  sha256(item['path']+item['name']).hexdigest())
            dirkey = "dir:{}:{}".format(node,sha256(item['path']).hexdigest())
            r.sadd(dirkey,k) # link to original folder
            r.hmset(k,item)
            if item['type'] == 'folder':
                r.hset(k,"dirlink",k.replace('store:','dir:'))

        print("Finished crawling " + HOST)
        # 300 seconds expiration
        nodeid = 'nodes:{}'.format(node)
        from time import time
        r.hset(nodeid,"created",time())
        r.expire(nodeid,300)
        recreate_index()
        r.srem("in-progress",node)

    if msg['channel'] == '__keyevent@0__:expired':
        node = node.split(':',1)[1] # nodes/ip:port
        print("delete files for node {}".format(node))
        for k in r.keys('dir:{}:*'.format(node)) + r.keys('store:{}:*'.format(node)):
            print("delete {}".format(k))
            r.delete(k)
        recreate_index()
