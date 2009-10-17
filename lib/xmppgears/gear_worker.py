#!/usr/bin/env python

from twisted.python import log
from twisted.internet import protocol, reactor, task

import json

from gearman import client
from xmppgears import xmpp_protocol, config

gear_worker = None

def run_test(j):
    print repr(j)
    return j

def update_presence(j):
    log.msg("update_presence called %s" % j)
    data = json.loads(j)
    return j

def send_plain(j):
    data = json.loads(j)
    log.msg("send_plain called %s" % j)
    xmpp_protocol.typing_notification(data["to"])
    xmpp_protocol.send_plain(data["to"], data["content"])
    

def send_html(j):
    data = json.loads(j.data)
    log.msg("send_html, data: %s" % repr(data))
    return j

def subscribe(j):
    log.msg("subscribe")
    print repr(j)
    return j

def unsubscribe(j):
    log.msg("unsubscribe")
    print repr(j)
    return j

def roster_list(j):
    log.msg("roster_list")
    return json.dumps(xmpp_protocol.rosters())

def add_function(funcname, function):
    global gear_worker
    funcname = config.CONF.get("gears", "prefix")+funcname
    gear_worker.registerFunction(funcname, function)    

def _register_functions():
    add_function("xmpp_presence_update", update_presence)
    add_function("xmpp_presence_subscribe", subscribe)
    add_function("xmpp_presence_unsubscribe", unsubscribe)
    add_function("xmpp_message_plain", send_plain)
    add_function("xmpp_message_html", send_html)
    add_function("xmpp_roster_list", roster_list)

def _connected(gearman):
    global gear_worker
    gear_worker = client.GearmanWorker(gearman)
    gear_worker.setId("xmpp-gears-woker")
    _register_functions()

    coop = task.Cooperator()
    for i in range(5):
        reactor.callLater(0.1 * i, lambda: coop.coiterate(gear_worker.doJobs()))

def connect():
    d = protocol.ClientCreator(reactor, client.GearmanProtocol).connectTCP(
        config.CONF.get("gears", "host"), config.CONF.getint("gears", "port"))
    d.addCallback(_connected)
    return d
