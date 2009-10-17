#!/usr/bin/env python
 
from __future__ import with_statement
 
import time
 
from twisted.python import log
from twisted.internet import protocol, reactor, threads
from twisted.words.xish import domish
from twisted.words.protocols.jabber.jid import JID
from twisted.words.protocols.jabber.xmlstream import IQ
 
from wokkel.xmppim import MessageProtocol, PresenceClientProtocol, RosterClientProtocol
from wokkel.xmppim import AvailablePresence

from xmppgears import gear_client

CHATSTATE_NS = 'http://jabber.org/protocol/chatstates'

message_conn = None
presence_conn = None
roster_conn = None

class XmppGearsMessageProtocol(MessageProtocol):

    def __init__(self, jid):
        super(XmppGearsMessageProtocol, self).__init__()
        self.jid = jid.full()

    def connectionInitialized(self):
        super(XmppGearsMessageProtocol, self).connectionInitialized()
        log.msg("Connected!")

        global message_conn
        message_conn = self

    def connectionLost(self, reason):
        log.msg("Disconnected!")

        global message_conn
        if message_conn == self:
            message_conn = None

        gear_client.submit("gear_connection_lost", "")

    def typing_notification(self, jid):
        """Send a typing notification to the given jid."""
 
        msg = domish.Element((None, "message"))
        msg["to"] = jid
        msg["from"] = self.jid
        msg.addElement((CHATSTATE_NS, 'composing'))
        self.send(msg)

    def create_message(self):
        msg = domish.Element((None, "message"))
        msg.addElement((CHATSTATE_NS, 'active'))
        return msg

    def send_plain(self, jid, content):
        msg = self.create_message()
        msg["to"] = jid
        msg["from"] = self.jid
        msg["type"] = 'chat'
        msg.addElement("body", content=content)
 
        self.send(msg)
 
    def send_html(self, jid, body, html):
        msg = self.create_message()
        msg["to"] = jid
        msg["from"] = self.jid
        msg["type"] = 'chat'
        html = u"<html xmlns='http://jabber.org/protocol/xhtml-im'><body xmlns='http://www.w3.org/1999/xhtml'>"+unicode(html)+u"</body></html>"
        msg.addRawXml(u"<body>" + unicode(body) + u"</body>")
        msg.addRawXml(unicode(html))
 
        self.send(msg)

    def onError(self, msg):
        log.msg("Error received for %s: %s" % (msg['from'], msg.toXml()))

    def onMessage(self, msg):
        log.msg("chat body message: %s" % msg.toXml())
        try:
            self.__onMessage(msg);
        except KeyError:
            log.err()

    def __onMessage(self, msg):
        if msg.getAttribute("type") == 'chat' and hasattr(msg, "body") and msg.body:
            gear_client.submit("gear_message_new", { "to": msg["to"], "from" : msg["from"], "from_bare": JID(msg["from"]).userhost(), "body": unicode(msg.body), "raw": msg.toXml().encode("utf-8")})
        else:
            log.msg("Non-chat/body message: %s" % msg.toXml())


class XmppGearsPresenceProtocol(PresenceClientProtocol):

    lost = None
    connected = None

    def __init__(self, jid):
        super(XmppGearsPresenceProtocol, self).__init__()
        self.jid = jid

    def connectionInitialized(self):
        super(XmppGearsPresenceProtocol, self).connectionInitialized()

        self.connected = time.time()

        global presence_conn
        presence_conn = self

        gear_client.submit("gear_presence_connected", "")
        self.available(None, None, { None: "ddd" }, 10)

    def connectionLost(self, reason):
        self.connected = None
        self.lost = time.time()

        
        # do gears

    def presence_fallback(self, *stuff):
        log.msg("Running presence fallback.")
        self.available(None, None, {None: "Hi, everybody!"})

        # do gears

    def _set_status(self, u, status, cb=None):
        if status is None:
            status = "available"

        log.msg("_set_status: %s %s" % (u, status))
        gear_client.submit("gear_presence_update", { "jid" : u, "status": status } )

    def available(self, entity=None, show=None, statuses=None, priority=0, avatar=None):
        presence = AvailablePresence(entity, show, statuses, priority)
        if avatar:
            presence.addElement(('vcard-temp:x:update', 'x')).addElement("photo", content=avatar)
        self.send(presence)

    def availableReceived(self, entity, show=None, statuses=None, priority=0):
        log.msg("Available from %s (%s, %s, pri=%s)" % (
            entity.full(), show, statuses, priority))

        # if priority >= 0 and show not in ['xa', 'dnd']:
        self._set_status(entity.userhost(), show)

        """
        if priority >= 0 and show not in ['xa', 'dnd']:
            scheduling.available_user(entity)
        else:
            log.msg("Marking jid unavailable due to negative priority or "
                    "being somewhat unavailable.")
            scheduling.unavailable_user(entity)
        self._find_and_set_status(entity.userhost(), show)
        """
 
    def unavailableReceived(self, entity, statuses=None):
        log.msg("Unavailable from %s" % entity.full())

        self._set_status(entity.userhost(), "offline")


    def subscribedReceived(self, entity):
        log.msg("Subscribe received from %s" % (entity.userhost()))

        self._set_status(entity.userhost(), "subscribed")

    def unsubscribedReceived(self, entity):
        log.msg("Unsubscribed received from %s" % (entity.userhost()))

        self.unsubscribe(entity)
        self.unsubscribed(entity)

        self._set_status(entity.userhost(), "unsubscribed")

    def subscribeReceived(self, entity):
        log.msg("Subscribe received from %s" % (entity.userhost()))
        self.subscribe(entity)
        self.subscribed(entity)

        self._set_status(entity.userhost(), "subscribe")

    def unsubscribeReceived(self, entity):
        log.msg("Unsubscribe received from %s" % (entity.userhost()))
        self.unsubscribe(entity)
        self.unsubscribed(entity)
        
        self._set_status(entity.userhost(), "unsubscribe")

class XmppGearsRosterProtocol(RosterClientProtocol):

    def __init__(self, jid):
        RosterClientProtocol.__init__(self)
        self.jid = jid

    def connectionInitialized(self):
        RosterClientProtocol.connectionInitialized(self)

        global roster_conn
        roster_conn = self

        self.getRoster()

    def onRosterSet(self, item):
        if not item.subscriptionTo and not item.subscriptionFrom and not item.ask:
            log.msg("Subscription of %s is none" % item.jid.userhost())

            self.removeItem(item.jid)

    def onRosterRemove(self, entity):
        log.msg("Roster %s removed" % entity.userhost())

        global presence_conn
        presence_conn._set_status(item.jid.userhost(), "unsubscribed")

def typing_notification(jid):
    message_conn.typing_notification(jid)

def send_html(jid, plain, html):
    message_conn.send_html(jid, plain, html)
 
def send_plain(jid, plain):
    message_conn.send_plain(jid, plain)
