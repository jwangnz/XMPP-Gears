#!/usr/bin/env python

import sys
sys.path.insert(0, "lib/wokkel")
sys.path.insert(0, 'lib/twisted-gears')
sys.path.insert(0, "lib")

from twisted.application import service
from twisted.internet import task, reactor
from twisted.words.protocols.jabber import jid
from twisted.web import client
from wokkel.client import XMPPClient
from wokkel.generic import VersionHandler
from wokkel.keepalive import KeepAlive
from wokkel.disco import DiscoHandler

from xmppgears import xmpp_protocol
from xmppgears import gear_client
from xmppgears import gear_worker

application = service.Application("xmpp-gears")

gear_client.connect()
gear_worker.connect()

j = jid.internJID("tsing@geowhy.org/xmppgears")
xmppclient = XMPPClient(jid.internJID("tsing@geowhy.org/xmppgears"), "tsinghaha", "geowhy.org")
xmppclient.logTraffic = False

protocols = [xmpp_protocol.XmppGearsMessageProtocol, xmpp_protocol.XmppGearsPresenceProtocol, xmpp_protocol.XmppGearsRosterProtocol ]
for p in protocols:
    handler = p(j)
    handler.setHandlerParent(xmppclient)

VersionHandler("XmppGears", "0.1").setHandlerParent(xmppclient)
KeepAlive().setHandlerParent(xmppclient)
xmppclient.setServiceParent(application)
