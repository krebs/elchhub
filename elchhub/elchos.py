import requests
from flask import Flask, render_template, request
import redis
import re
import os
import logging
from hashlib import sha256

ttl = 300
r = redis.StrictRedis(host='localhost', port=6379, db=0)


app = Flask(__name__, static_folder="static")
log = app.logger

#Start the HTTP server
@app.route("/favicon.ico")
def return_favicon(): return ""

@app.route("/api/ping", methods=["POST"])
def register_node():
    """
sar 1 3 | grep Average | awk -F " " '{print (100 - $8)"%"}'
sar -n DEV 1 3 | grep Average |grep ppp0 | awk -F " " '{print ($6) "txkB/s"}
{print ($5) "rxkB/s"} '

    """
    nodes = r.keys('nodes:*')
    data= request.get_json(force=True)
    host = data["IP"]
    port = data.get("PORT","21")
    load = data.get("load",-1)
    cpu = data.get("cpu",-1)
    rx = data.get("net-rx",-1)
    tx = data.get("net-rx",-1)

    node = host + ":" + port
    nodekey = "nodes:"+node
    #Search for the server in the known servers
    if nodekey in nodes:
        print("server {} is alive, refreshing ttl".format(node))
        r.expire(nodekey,ttl)
        return "refresh"
    if r.sismember("in-progress",node):
        print("Crawl in progress for {}".format(node))
        return "crawl in progress"
    else:
        print("New node " + node)
        r.publish("new_node",node)
        return "new node"


def get_content(e):
    data = r.hgetall(e)
    try: data['size'] = int(data['size'])
    except: pass
    return data

def update_content_list(hm,e,score=None):
    """
    if not existing, adds content to hashmap
    if existing, adds the nodename to nodes list of content
    """
    data = get_content(e)
    fullpath = os.path.join(data['path'],data["name"]).strip("/")
    nodename = ":".join(e.split(':',2)[1:2])
    data['nodes'] = [nodename]
    data['fullpath'] = fullpath
    if score is not None:
        data['score'] = score
    if fullpath in hm:
        hm[fullpath]['nodes'].append(nodename)
    else:
        hm[fullpath] = data

@app.route("/api/search", methods=["POST"])
def search_files():
    from random import randint
    nodes = list(r.scan_iter('nodes:*'))
    found_content = {}
    query = request.form["searchterm"]
    searchkey = "search:query:{}".format(sha256(query)) # we use this to collect results
    search_terms = filter(None,re.split("[\W_]",query.lower()))
    for search_term in search_terms:
        for val,score in r.zrevrange("search:index:{}".format(
                re.escape(search_term)),0,1000,withscores=True):
            r.zincrby(searchkey,val,score)

    for val,score in r.zrevrange(searchkey,0,1000,withscores=True):
        update_content_list(found_content,val,score)

    return render_template(
        "listing.html",
        content=sorted(found_content.values(),key=lambda x:-x["score"]),
        site_title="Search for " + query,
        nodecount=len(nodes)
    )

@app.route("/", defaults={"path": ""}, methods=["GET"])
@app.route("/<path:path>", methods=["GET"])
def catch_all(path):
    nodes = r.keys('nodes:*')
    import re
    folder_content = {}
    path = path.strip('/')
    print(path)
    key = sha256(path).hexdigest()

    for k in r.scan_iter(match='dir:*:{}'.format(key)):
        for e in r.smembers(k):
            update_content_list(folder_content,e)

    folder_content = folder_content.values()
    print("Files in " + path + ": " + str(folder_content))
    return render_template(
            "listing.html",
            content=sorted(folder_content),
            site_title="Listing of " + path if path!="" else "Welcome to elchOS (" + str(len(nodes)) + " nodes)",
            nodecount=len(nodes)
    )

if __name__ == '__main__':
    app.run(debug=True)
