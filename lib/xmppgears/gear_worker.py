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
    data = json.loads(j)
    xmpp_protocol.available(data["show"], data["status"], data["priority"], data["avatar"])

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

class GearmanWorkerProtocol(client.GearmanProtocol):
    def makeConnection(self, transport):
        global gear_worker
        client.GearmanProtocol.makeConnection(self, transport)
        gear_worker = client.GearmanWorker(self)
        gear_worker.setId("xmpp-gears-woker")
        _register_functions()

        coop = task.Cooperator()
        for i in range(5):
            reactor.callLater(0.1 * i, lambda: coop.coiterate(gear_worker.doJobs()))

class GearmanWorkerFactory(protocol.ReconnectingClientFactory):
    def startedConnecting(self, connector):
        log.msg("Started to connect gearman as worker")

    def buildProtocol(self, addr):
        self.resetDelay()
        log.msg("Connected to gearman as worker.")

        gearman = GearmanWorkerProtocol()
        return gearman

    def clientConnectionLost(self, connector, reason):
        log.msg("Lost connection of gearman worker. Reason: %s" % reason)
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log.msg("Connection failed of gearman worker. Reason: %s" % reason)
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

def connect():
    connector = reactor.connectTCP(config.CONF.get("gears", "host"), config.CONF.getint("gears", "port"),
        GearmanWorkerFactory())
