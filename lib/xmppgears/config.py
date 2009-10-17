#!/usr/bin/env python

import ConfigParser
import commands

CONF=ConfigParser.ConfigParser()
CONF.read("xmppgears.conf")
VERSION=commands.getoutput("git describe").strip()
ADMINS=CONF.get("general", "admins").split(' ')
