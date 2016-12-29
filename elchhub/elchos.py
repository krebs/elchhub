import requests
from flask import Flask, render_template, request
import redis
import re
import os
import logging
from hashlib import sha256

ttl = 300
r = redis.StrictRedis(host='localhost', port=6379, db=0,decode_responses=True)


app = Flask(__name__, static_folder="static")
app.config['PROPAGATE_EXCEPTIONS'] = True
log = app.logger

#Start the HTTP server
@app.route("/favicon.ico")
def return_favicon(): return ""

@app.route("/api/node/<node>",methods=["DELETE"])
def unregister_node(node):
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr

    nodes = r.smembers('node-index')
    nodekey = "nodes:"+node
    if node in nodes:
        if node.startswith(ip+":"):
            # expire node immediately
            r.expire(nodekey,1)
            return "ok"
        else:
            return "unauthorized",401
    elif r.sismember("in-progress",node):
        print("crawl in progress for {}".format(node))
        return "crawl in progress, stay tuned",420
    else:
        print("cannot remove unknown node {}".format(node))
        return "unknown node",404

@app.route("/api/ping", methods=["POST"])
def register_node():
    """
sar 1 3 | grep Average | awk -F " " '{print (100 - $8)"%"}'
sar -n DEV 1 3 | grep Average |grep ppp0 | awk -F " " '{print ($6) "txkB/s"}
{print ($5) "rxkB/s"} '

    """
    nodes = r.smembers('node-index')
    data= request.get_json(force=True)
    host = data["IP"]
    port = data["PORT"]
    node = host + ":" + port
    port = data.get("PORT","21")


    nodekey = "nodes:"+node
    #Search for the server in the known servers
    if node in nodes:
        print("server {} is alive, refreshing ttl".format(node))
        r.expire(nodekey,ttl)
        return "refresh"
    if r.sismember("in-progress",node):
        print("Crawl in progress for {}".format(node))
        return "crawl in progress"
    else:
        print("New node " + node)
        r.publish("new_node",node)
        # TODO do not directly set here
        r.hmset(nodekey, data)
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
    hostkey = e.replace("store:","hostrevlink:")
    data = get_content(e)
    fullpath = os.path.join(data['path'],data["name"]).strip("/")
    # import pdb;pdb.set_trace()
    data['nodes'] = list(r.smembers(hostkey))
    # log.debug(data)
    data['fullpath'] = fullpath
    if score is not None:
        data['score'] = score
    hm[fullpath] = data

@app.route("/api/search", methods=["POST"])
def search_files():
    from random import randint
    num_nodes = r.scard('node-index')
    found_content = {}
    query = request.form["searchterm"]
    # use the normalized search terms
    search_terms = sorted(filter(None,re.split("[\W_]",query.lower())))
    searchkey = "search:query:{}".format(sha256(str(search_terms).encode()).hexdigest()) # we use this to collect results

    if r.zcard(searchkey) != 0:
        print("Found previous search for query {},normalized {} ({})".format(
                    query,search_terms,searchkey))
    else: # start the search
        print("Starting new search for query {}, normalized {}".format(query,search_terms))
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
        nodecount=num_nodes
    )

@app.route("/", defaults={"path": ""}, methods=["GET"])
@app.route("/<path:path>", methods=["GET"])
def catch_all(path):
    # TODO: check if it would be worth creating a separate nodes index
    num_nodes = r.scard('node-index')
    allnodeids = r.smembers('node-index')
    allhosts = {n.replace("nodes:",""): r.hgetall(n) for n in r.keys("nodes:*")}
    print("all Hosts:" + str(allhosts))
    import re
    folder_content = {}
    path = path.strip('/')
    print(path)
    key = sha256(path.encode()).hexdigest()

    # DIRLISTING via dirlink:
    dirkey = "dirlink:"+ key
    for e in r.smembers(dirkey):
        update_content_list(folder_content,e)

    folder_content = folder_content.values()
    log.debug("Files in " + path + ": " + str(folder_content))
    return render_template(
            "listing.html",
            content=sorted(folder_content,
                key=lambda x: x['fullpath'].lower()),
            site_title="Listing of " + path if path!="" else "Welcome to elchOS (" + str(num_nodes) + " nodes)",
            nodecount=num_nodes,
            allhosts=allhosts
    )

if __name__ == '__main__':
    app.run(debug=True)
