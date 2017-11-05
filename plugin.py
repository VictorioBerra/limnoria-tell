###
# Copyright (c) 2017, Brandon Cain, Victorio Berra
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import datetime

import supybot.callbacks as callbacks
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.conf as conf
from supybot.commands import *
import os
import humanize

from .local.tell_db import TellDB

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Tell')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


# Used to query tells for users.
class TellLib:

    # to_nic => {'tells'=>[], 'delay'=>datetime.datetime}
    unread_tells = {}

    # Initial tell count (Or after reload)
    tell_count = 0

    # Query post (past) tells
    def query_post(self, user: str):
        if user in self.unread_tells:
            return self.unread_tells[user]
        else:
            return None

    def flag_all_read(self, nick):
        _tells = self.unread_tells.copy()

        if nick not in _tells:
            return

        for i in _tells[nick]['tells']:
            _id = i['id']

            self.message_read(_id, nick, skip_index=True)

        # Delete here after we have flagged in DB
        del self.unread_tells[nick]

    # Load all unread messages into memory
    def load_unread(self):
        # telrefresh, done...
        self.unread_tells = {}
        self.tell_count = 0
        for record in TellDB.query_unread():
            self.tell_count += 1
            _r = {'id': record.ID, 'content': record.Content, 'time': record.Timestamp, 'private': record.Private,
                  'from': record.FromNick}
            if record.ToNick in self.unread_tells:
                self.unread_tells[record.ToNick]['tells'].append(_r)
            else:
                self.unread_tells[record.ToNick] = {'tells': [_r], 'delay': None}

    # Sync database and set a message to read
    def message_read(self, tell_id, nick, skip_index=False):
        TellDB.update_read(tell_id)

        if skip_index:
            return
        else:
            del self.unread_tells[nick]

    def set_delay(self, nick, delay):
        if nick in self.unread_tells:
            self.unread_tells[nick]['delay'] = delay

    # TellDB.insert_tell(msg.nick, i, message, self.pm, _dt)
    def insert_tell(self, from_nick, to_nick, message, private, time):
        record_id = TellDB.insert_tell(from_nick, to_nick, message, private, time)

        _r = {'id': record_id, 'content': message, 'time': time, 'private': private, 'from': from_nick}

        if to_nick in self.unread_tells:
            self.unread_tells[to_nick]['tells'].append(_r)
        else:
            self.unread_tells[to_nick] = {'tells': [_r], 'delay': None}

    def get_tell_count(self):
        return self.tell_count

    def get_user_tell_count(self, nick):
        if nick in self.unread_tells:
            return len(self.unread_tells[nick])
        else:
            return 0


class Tell(callbacks.Plugin):
    """MemoServ replacement with extra features."""

    # If we're using SQLite, we better (should) be testing. Need this to be false so SQLite will work.
    if 'IRC_BOT_DEV' in os.environ and os.environ['IRC_BOT_DEV'] == "1":
        threaded = False
    else:
        threaded = True

    queryTell = TellLib()

    pm = 0

    # Commands that won't query tells
    no_tells = ['delaytells', 'skiptells']

    def __init__(self, irc):
        self.__parent = super(Tell, self)
        self.__parent.__init__(irc)

        self.queryTell.load_unread()

        # Build the list for no tells
        self.bypass_tell_query = []
        _chars = conf.supybot.reply.whenAddressedBy.chars()
        _chars = _chars.split(',')
        for i in self.no_tells:
            self.bypass_tell_query.append(i)
            for c in _chars:
                self.bypass_tell_query.append("%s%s" % (c, i))

    def get_timeago(self, t):
        return humanize.naturaltime(datetime.datetime.now() - t['time'])

    # Process all text before handing off to command processor
    def inFilter(self, irc, msg):
        # If !delaytells is the command, obviously don't relay tells.
        # Test environment strips the ! for some odd fucking reason...
        if msg.args[1].split(' ')[0] in self.bypass_tell_query:
            return msg

        # Attempt to query any past tells for the user.
        if msg.command == "PRIVMSG":
            tells = self.queryTell.query_post(msg.nick)
            _channel = msg.args[0]

            # Sending PM to bot?
            if _channel == irc.nick:
                self.pm = True
            else:
                # Check that we have a valid channel
                if not ircutils.isChannel(_channel) and _channel != 'test':
                    return msg
                self.pm = False

            # Process any tells for the user when they type
            if tells is not None:
                # First check if we have a delay.
                if tells['delay'] is not None:
                    _now = datetime.datetime.now()
                    try:
                        if _now < tells['delay']:
                            # Don't relay tells. We haven't passed the delay time
                            return msg
                    except:
                        pass

                _public = self.registryValue('you_have_mail')
                _private = self.registryValue('you_have_private_mail')
                _message = self.registryValue("tell_message")
                _priv_tells = []
                _pub_tells = []
                _relay_pub = False
                _relay_private = False
                _priv_count = 0
                _pub_count = 0
                # Format and divvy out private and public tells.
                for t in tells['tells']:
                    # Set the Tell to read
                    _id = t['id']
                    self.queryTell.message_read(_id, msg.nick)
                    # This will tie to config, tellMessage. If you want to add more variables, do it here.
                    _d = {'time_ago': self.get_timeago(t), 'from': t['from'], 'content': t['content']}
                    if t['private'] is True:
                        _priv_count += 1
                        _relay_private = True
                        _priv_tells.append(_message.format(**_d))
                    elif t['private'] is False:
                        _pub_count += 1
                        _relay_pub = True
                        _pub_tells.append(_message.format(**_d))

                # Relay public tells
                if _relay_pub:
                    _m = _public.format(**{
                        'to': msg.nick,
                        'pub_count': _pub_count,
                        'plural': "s" if _pub_count > 1 else ''
                    })
                    irc.queueMsg(ircmsgs.notice(_channel, _m))

                    for m in _pub_tells:
                        irc.queueMsg(ircmsgs.notice(_channel, m))

                # Relay private tells
                if _relay_private:
                    _m = _private.format(**{
                        'to': msg.nick,
                        'priv_count': _priv_count,
                        'plural': "s" if _priv_count > 1 else ''
                    })
                    irc.queueMsg(ircmsgs.notice(msg.nick, _m))

                    for m in _priv_tells:
                        irc.queueMsg(ircmsgs.notice(msg.nick, m))
        return msg

    def tell(self, irc, msg, args, now, nicks, message):
        """<user1,user2> <message>
    
        Saves a tell for the specified nicks.
        """
        tell_to = nicks.split(',')

        # Insert tell records per each nick name
        _dt = datetime.datetime.now()
        for i in tell_to:
            self.queryTell.insert_tell(msg.nick, i, message, self.pm, _dt)

        irc.queueMsg(ircmsgs.notice(msg.nick, "Saving tell '" + message + "' for " + nicks))
    tell = wrap(tell, ['now', 'somethingWithoutSpaces', 'text'])

    def skiptells(self, irc, msg, args):
        """
        Skip all tells and set to Read.
        """
        _count = self.queryTell.get_user_tell_count(msg.nick)
        _message = self.registryValue("tell_skip")
        self.queryTell.flag_all_read(msg.nick)

        irc.queueMsg(ircmsgs.notice(msg.nick, _message.format(**{"count": _count})))

    skiptells = wrap(skiptells, [])

    def tellrefresh(self, irc, msg, args):
        """
        Refresh the unread tells from Database
        """

        self.queryTell.load_unread()
        _r = self.registryValue("tell_refresh")
        irc.queueMsg(ircmsgs.notice(
                msg.nick,
                _r.format(**{'count': self.queryTell.get_tell_count()})
            )
        )

        return True

    tellrefresh = wrap(tellrefresh, ['admin'])

    def delay_tells(self, irc, msg, args, time):
        """
        Delay tells x time
        """

        _parts = time.split(' ')

        if len(_parts) == 2:
            try:
                count = int(_parts[0])
                # Pull off the s from a plural interval
                interval = _parts[1] if _parts[1][-1] != 's' else _parts[1][0:-1]

            except ValueError:
                irc.reply("Please input valid time frame. ie: 2 hours")
                return

            if interval == 'second':
                _seconds = 1
            elif interval == 'minute':
                _seconds = 60
            elif interval == 'hour':
                _seconds = 3600
            elif interval == 'day':
                _seconds = 86400
            else:
                irc.reply("Please input valid time frame. ie: 2 hours")
                return

            _delay = datetime.datetime.now() + datetime.timedelta(seconds=_seconds*count)
            self.queryTell.set_delay(msg.nick, _delay)

            irc.queueMsg(ircmsgs.notice(msg.nick, "Beep boop beep. Tells have been delayed."))

        else:
            irc.reply("Please input valid time frame. ie: 2 hours")
        pass

    delaytells = wrap(delay_tells, ['text'])


Class = Tell


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
