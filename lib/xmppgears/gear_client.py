#!/usr/bin/env python

from twisted.python import log
from twisted.internet import protocol, reactor

import json

from gearman import client
from xmppgears import config

gear_client = None

class GearmanClientProtocol(client.GearmanProtocol):
    def makeConnection(self, transport):
        global gear_client
        client.GearmanProtocol.makeConnection(self, transport)
        gear_client = client.GearmanClient(self)

class GearmanClientFactory(protocol.ReconnectingClientFactory):
    def startedConnecting(self, connector):
        log.msg("Started to connect to gearman as client")

    def buildProtocol(self, addr):
        self.resetDelay()
        log.msg("Connected to gearman as client")

        gearman = GearmanClientProtocol()
        return gearman

    def clientConnectionLost(self, connector, reason):
        log.msg("Lost connection of gearman client. Reason: %s" % reason)
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log.msg("Connection failed of gearman client. Reason: %s" % reason)
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

def connect():
    connector = reactor.connectTCP(config.CONF.get("gears", "host"), config.CONF.getint("gears", "port"),
        GearmanClientFactory())

def submit(funcname, data):
    log.msg("gear_client submit %s" % funcname)
    data = json.dumps(data)
    funcname = config.CONF.get("gears", "prefix")+funcname
    gear_client.submitBackground(funcname, data)
