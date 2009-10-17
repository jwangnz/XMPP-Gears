#!/usr/bin/env python

from twisted.python import log
from twisted.internet import protocol, reactor

import json

from gearman import client
from xmppgears import config

gear_client = None


#@defer.inlineCallbacks
def _connected(gearman):
    global gear_client
    gear_client = client.GearmanClient(gearman)

def connect():
    d = protocol.ClientCreator(reactor, client.GearmanProtocol).connectTCP(
        config.CONF.get("gears", "host"), config.CONF.getint("gears", "port"))
    d.addCallback(_connected)
    return d

def submit(funcname, data):
    log.msg("gear_client submit %s" % funcname)
    data = json.dumps(data)
    funcname = config.CONF.get("gears", "prefix")+funcname
    gear_client.submitBackground(funcname, data)
