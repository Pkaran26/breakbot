#!/usr/bin/python
# Copyright 2012 Bruno Gonzalez
# This software is released under the GNU AFFERO GENERAL PUBLIC LICENSE (see agpl-3.0.txt or www.gnu.org/licenses/agpl-3.0.html)

import threading
import time
from irc_bot import IRCInterface
from wa_bot import WAInterface

def store_msg(message, file_path=None):
    if file_path is None:
        raise Exception("No file specified!")
    text = message.serialize() + "\n"
    with open(file_path, "a") as log:
        log.write(text)
def channels_from_contacts(contacts):
    channels = []
    for k,v in contacts.items():
        if v.startswith("#"):
            channels.append(v)
    channels.append("#botdebug")
    return channels
    
class Bot(threading.Thread):
    def __init__(self, wa_phone, wa_identifier, contacts, irc_server, irc_port):
        threading.Thread.__init__(self)
        self.must_run = False
        self.irc_server = irc_server
        self.irc_port = irc_port
        self.wa_phone = wa_phone
        irc_nick = contacts[wa_phone]
        self.irc_nick = irc_nick
        self.wa_identifier = wa_identifier
        self.contacts = contacts
        self.irc_i = IRCInterface(self.irc_server, self.irc_port, self.irc_nick, channels_from_contacts(self.contacts), self.irc_msg_received, self.stop)
        self.wa_i = WAInterface(self.wa_phone, self.wa_identifier, self.wa_msg_received, self.stop)
    def run(self):
        self.must_run = True
        try:
            self.irc_i.start()
            self.irc_i.wait_connected()
            self.wa_i.start()
            self.wa_i.wait_connected()
        except Exception, e:
            print "Exception while running bot: %s" %e
            self.stop()
    def stop(self):
        self.must_run = False
        self.irc_i.stop()
        self.wa_i.stop()

    def irc_msg_received(self, message):
        def get_group_from_chan(contacts, irc_channel):
            for k,v in contacts.items():
                if v == irc_channel:
                    return k
            raise Exception("Channel not found in contact list")

        store_msg(message, "/tmp/log.txt")
        print " <<< Received IRC message: %s" %message

        msg = "<%s> %s" %(message.get_nick(), message.msg)
        try:
            group = get_group_from_chan(self.contacts, message.chan)
            self.wa_i.send(group, msg)
        except Exception,e:
            print "Channel %s not recognized: %s" %(message.chan, e)


    def wa_msg_received(self, message):
        store_msg(message, "/tmp/log.txt")
        print " <<< Received WA message: %s" %message
        if message.chan == self.wa_phone:
            #private message
            if message.target is None:
                # directed to bot itself
                nick = self.contacts[message.get_nick()]
                msg = "<%s> %s" %(nick, message.msg)
                self.irc_i.send("#botdebug", message.msg)  #TODO: lookup
            else:
                # directed to someone
                try:
                    phone = message.get_nick()
                    nick = self.contacts[phone]
                    target = message.target # get IRC nick from contacts
                                            # if not already a nick
                    msg = "<%s> %s" %(target, message.msg)
                    self.irc_i.send("#botdebug", msg)
                except Exception,e:
                    print "Couldn't relay directed WA msg to IRC: %s" %(e)
        else:
            #group message
            try:
                msg = "<%s> %s" %(self.contacts[message.get_nick()], message.msg)
            except Exception,e:
                print "Contact not recognized: %s" %e
                msg = "<%s> %s" %(message.get_nick(), message.msg)
            try:
                self.irc_i.send(self.contacts[message.chan], msg)
            except Exception,e:
                print "Channel %s not recognized: %s" %(message.chan, e)


contacts = {
    "34555555125": "my_bot"
   ,"34555555373": "person1"
   ,"34555555530": "person2"
   ,"34555555806": "person3"
   ,"34555555565": "person4"
   ,"34555555602": "person5"
   ,"34555555373-1352752705@g.us": "#sample_room"
   ,"34555555530-1321985629@g.us": "#sample_room2"
}
print "%s" %contacts

print "Program started"
b = Bot("34555555125", "", contacts, "irc.freenode.net", 6667)
try:
    b.start()
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    print "User wants to stop"
finally:
    b.stop()
print "Program finished"
