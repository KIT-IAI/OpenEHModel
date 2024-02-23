import ast
import redis
import sys
import time
import json


def engage_redis(cluster, channel):
    if cluster:
        r = redis.StrictRedis(host="redis.webis", port=6379)
    else:
        r = redis.StrictRedis(host="127.0.0.1", port=6379)
    stream = r.pubsub()
    stream.subscribe(channel)
    return r, stream


def send_redis(schedule, redis_instance):
    redis_instance.publish("algorithm.EA.epoch.1", json.dumps(schedule))


def wait_for_stream(stream):
    i = 0
    while True:
        values = stream.get_message()
        if not values:
            i = loading_symbol("Waiting for new Values.", i)
        elif values["data"] != 1:
            break
    values = ast.literal_eval(values["data"].decode("UTF-8"))
    return values


def loading_symbol(message, counter=0):
    sys.stdout.write(message + " " + "|/-\\"[(counter % 4)])
    sys.stdout.flush()
    time.sleep(1)
    sys.stdout.write((len(message) + 2) * "\b")
    return counter + 1
