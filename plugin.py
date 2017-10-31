###
# Copyright (c) 2017, Brandon Cain
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
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.ircmsgs as ircmsgs
import supybot.callbacks as callbacks
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
import os
import humanize

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Tell')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

Base = declarative_base()


# Used to query tells for users.
class PostTell:

    # to_nic => ((tell_id, message, time, private, from_nick), )
    unread_tells = {}

    # Query post (past) tells
    def query_post(self, user: str):
        # TODO: Query past tell messages for when user types anything
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
        for record in session.query(TellRecord).filter(TellRecord.Read == 0).all():
            _r = {'id': record.ID, 'content': record.Content, 'time': record.Timestamp, 'private': record.Private,
                  'from': record.FromNick}
            if record.ToNick in self.unread_tells:
                self.unread_tells[record.ToNick]['tells'].append(_r)
            else:
                self.unread_tells[record.ToNick] = {'tells': [_r], 'delay':None}

        session.commit()

    # Sync database and set a message to read
    def message_read(self, tell_id, nick, skip_index=False):
        stmt = TellRecord.__table__.update().where(TellRecord.ID == tell_id).values(Read=True)
        session.execute(stmt)
        session.commit()

        if skip_index:
            return
        else:
            del self.unread_tells[nick]

    def delay_tells(self, nick, delay):
        if nick in self.unread_tells:
            self.unread_tells[nick]['delay'] = delay


class TellRecord(Base):
    __tablename__ = 'tell'
    # Here we define columns for the table person
    # Notice that each column is also a normal Python instance attribute.
    ID = Column(Integer, primary_key=True)
    FromNick = Column(String(255), nullable=False)
    ToNick = Column(String(255), nullable=False)
    Content = Column(String(255), nullable=False)
    Private = Column(Boolean())
    Read = Column(Boolean())
    Timestamp = Column(DateTime(), nullable=False)


# Create an engine that stores data in the local directory's
# sqlalchemy_example.db file.
engine = create_engine(os.environ['TELL_CONNECTION_STRING'])


# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


class Tell(callbacks.Plugin):
    """MemoServ replacement with extra features."""
    threaded = True

    queryTell = PostTell()

    pm = 0

    def __init__(self, irc):
        self.__parent = super(Tell, self)
        self.__parent.__init__(irc)

        # TODO: Load all unread messages.
        self.queryTell.load_unread()

    # Process all text before handing off to command processor
    def inFilter(self, irc, msg):
        # Return days, hours, minutes ago with *simple* logic
        def get_timeago():
            return humanize.naturaltime(datetime.datetime.now() - t['time'])

        # If !delaytells is the command, obviously don't relay tells.
        if str(msg).find('!delaytells') != -1 or str(msg).find('!skiptells') != -1:
            return msg

        # Attempt to query any past tells for the user.
        if msg.command == "PRIVMSG":
            tells = self.queryTell.query_post(msg.nick)
            _channel = msg.args[0]

            # Sending PM to bot?
            if _channel == irc.nick:
                self.pm = 1
            else:
                # Check that we have a valid channel
                if not ircutils.isChannel(_channel):
                    return msg
                self.pm = 0

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

                _public = self.registryValue('youhavemail')
                _private = self.registryValue('youhaveprivatemail')
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
                    _d = {'time_ago': get_timeago(), 'from': t['from'], 'content': t['content']}
                    if t['private'] is True:
                        _priv_count += 1
                        _relay_private = True
                        _priv_tells.append(self.registryValue("tellMessage").format(**_d))
                    elif t['private'] is False:
                        _pub_count += 1
                        _relay_pub = True
                        _pub_tells.append(self.registryValue("tellMessage").format(**_d))

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
            new_tell = TellRecord(FromNick=msg.nick, ToNick=i, Content=message, Private=self.pm, Read=0,
                                  Timestamp=_dt)
            session.add(new_tell)

        session.commit()

        irc.queueMsg(ircmsgs.notice(msg.nick, "Saving tell '" + message + "' for " + nicks))
    tell = wrap(tell, ['now', 'somethingWithoutSpaces', 'text'])

    def skiptells(self, irc, msg, args):
        """
        Skip all tells and set to Read.
        """
        self.queryTell.flag_all_read(msg.nick)

        irc.queueMsg(ircmsgs.notice(msg.nick, "Beep boop beep. Skipping all tells."))

    skiptells = wrap(skiptells, [])

    def tellrefresh(self, irc, msg, args):
        """
        Refresh the unread tells from Database
        """

        self.queryTell.load_unread()

        irc.queueMsg(ircmsgs.notice(msg.nick, "Beep boop beep. Tells have been reloaded from the database."))

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
            self.queryTell.delay_tells(msg.nick, _delay)

            irc.queueMsg(ircmsgs.notice(msg.nick, "Beep boop beep. Tells have been delayed."))

        else:
            irc.reply("Please input valid time frame. ie: 2 hours")
        pass

    delaytells = wrap(delay_tells, ['text'])


Class = Tell


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
