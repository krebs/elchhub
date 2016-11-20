#!/usr/bin/env python

from .Crawler import FTP_Crawler
import minibar
import redis
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('elch-manager')

def main():
    r = redis.StrictRedis(host='localhost', port=6379, db=0,decode_responses=True)
    pubsub = r.pubsub()
    r.config_set('notify-keyspace-events','KEA')
    minibar_tpl = "{i}/{total} {bar} {elapsed}s {eta}"

    #pubsub.psubscribe('*')
    pubsub.subscribe('__keyevent@0__:expired')
    pubsub.subscribe('new_node')
    pubsub.subscribe('delete_node')
    pubsub.subscribe('update_node')

    def cleanup_search_index():
        log.info("search index cleanup")
        for k in r.scan_iter(match="search:index:*") :
            r.delete(k)
        for k in r.scan_iter("search:query:*"): #invalidate previous searches
            r.delete(k)

    def recreate_index():
        # TODO: lock if index is currently being recreated
        import re
        # cleanup index

        # TODO: do the cleanup when a host gets removed, not clean up the whole thing
        cleanup_search_index()
        log.info("starting index recreation")
        store_size = len(list(r.scan_iter(match="store:*")))
        pipe = r.pipeline()
        for idx,k in enumerate(r.scan_iter(match="store:*")):
            v = r.hgetall(k)
            if idx % 1000 == 0: log.info("{} of {}".format(idx,store_size))
            if idx % 10000 == 0:
                log.info("executing pipeline")
                pipe.execute()

            # TODO tokenize with nltk instead of this
            # TODO: remove stopwords

            # add index for keywords in name
            for token in filter(None,
                    set(re.split("[\W_]",v["name"].lower()))):
                # folders value more than files if they match the token
                pipe.zadd("search:index:" + token,20 if v["type"] == "folder" else 10,k)

            # add index for keywords in path
            pathlist = v["path"].lower().split("/")
            for idx,directory in enumerate(reversed(pathlist)):
                for token in filter(None,set(re.split("[\W_]",directory))):
                    score = 9 - idx if idx < 9 else 1
                    pipe.zincrby("search:index:" + token,k,score)
        pipe.execute()

    log.info("ready for receiving messages")
    for msg in pubsub.listen():
        log.debug(msg)
        if msg['type'] == 'subscribe':continue
        node = msg['data']
        channel = msg['channel']
        if channel == 'update_node':
            log.info('extend ttl for {}'.format(node))
            r.expire("nodes:{}".format(node),300)
        if channel == 'new_node':
            #Crawl this server
            log.info("Starting to crawl " + node)
            HOST,PORT = node.split(':')
            r.sadd("in-progress",node)
            crawler = FTP_Crawler(HOST, int(PORT))
            content_list = crawler.crawl()

            from hashlib import sha256
            pipe = r.pipeline()
            content_size = len(content_list)
            for idx,item in enumerate(content_list):
                if idx % 1000 == 0:
                    log.info("{} of {}".format(idx,content_size))
                if idx % 10000 == 0:
                    log.info("executing pipeline")
                    pipe.execute()
                p = item['path'].encode()
                fp = p+item['name'].encode()
                k = "store:{}".format(sha256(fp).hexdigest())
                dirkey = "dirlink:{}".format(sha256(p).hexdigest())
                hostkey = "hostlink:{}".format(node)
                hostrevkey = k.replace("store:","hostrevlink:")
                item['dirlink'] = dirkey
                pipe.sadd(dirkey,k)     # link to original folder
                pipe.sadd(hostkey,k)    # link file to host
                pipe.sadd(hostrevkey,node) # link host to file
                pipe.hmset(k,item)

            pipe.execute()
            log.info("Finished crawling {}".format(HOST))
            nodeid = 'nodes:{}'.format(node)
            from time import time
            log.info("Starting indexing")
            recreate_index()
            log.info("finished indexing")
            r.hset(nodeid,"created",time())
            r.sadd("node-index",node)
            # 300 seconds expiration
            r.expire(nodeid,300)
            r.srem("in-progress",node)

        if channel == '__keyevent@0__:expired' or channel == "delete_node":
            node = node.split(':',1)[1] # nodes:ip:port
            log.info("delete files for node {}".format(node))
            hkey = 'hostlink:{}'.format(node)
            nkey = 'nodes:{}'.format(node)
            for k in r.sscan_iter(hkey):
                log.debug("delete {}".format(k))
                hostrevkey = k.replace("store:","hostrevlink:")
                dirlink = r.hget(k,"dirlink")
                log.debug("removing {} from {}".format(k,hostrevkey))
                r.srem(hostrevkey,node)
                if len(r.smembers(hostrevkey)) == 0:
                    log.debug("availablity to 0 again, cleaning up dirlink")
                    r.srem(dirlink,k)
                    r.delete(k)
            r.delete(hkey)
            r.delete(nkey)
            r.srem("node-index",node)
            recreate_index()

if __name__ == "__main__":
    main()
