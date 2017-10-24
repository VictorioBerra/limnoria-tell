###
# Copyright (c) 2017, Victorio Berra
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
import supybot.callbacks as callbacks
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

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
    
    @staticmethod
    def query_post(user: str):
        # TODO: Query past tell messages for when user types anything
        print(user)


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

    # Process all text before handing off to command processor
    def inFilter(self, irc, msg):
        # Attempt to query any past tells for the user.
        if msg.command == "PRIVMSG":
            self.queryTell.query_post(msg.nick)

        return msg

    def tell(self, irc, msg, args, now, nicks, message):
        """<user1,user2> <message>
    
        Saves a tell for the specified nicks.
        """

        tell_to = nicks.split(',')

        # Insert tell records per each nick name
        _dt = datetime.datetime.now()
        for i in tell_to:
            new_tell = TellRecord(FromNick=msg.nick, ToNick=i, Content=message, Private=0, Read=0,
                                  Timestamp=_dt)
            session.add(new_tell)

        session.commit()

        irc.reply(str("Saving tell '" + message + "' for " + nicks))
    tell = wrap(tell, ['now', 'somethingWithoutSpaces', 'text'])


Class = Tell


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
