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

from supybot.test import *
import supybot.conf as conf


class TellTestCase(PluginTestCase):
    plugins = ('Tell',)
    _user1 = 'foo!bar@baz'
    _user2 = 'bar!foo@baz'
    
    def setUp(self):
        PluginTestCase.setUp(self)
        # global tester
        self.prefix = self._user2
    
    def testTell(self):
        # PM Bot with tell message
        self.assertNotError('tell foo hello world')
        self.prefix = self._user1

        _m = conf.supybot.plugins.tell.tell_message()
        assert(_m is not None)
        # Private response.
        _pr = conf.supybot.plugins.tell.you_have_private_mail()
        assert(_pr is not None)
        self.assertResponse("Hey hows it going", _pr.format(**{'to': 'foo', 'priv_count': 1, 'plural': ''}), to="#test_channel")
        self.assertResponse(" ", _m.format(**{"time_ago": "now", "from": "bar", "content": "hello world"}), to="#test_channel")  # Pick up the last piece as well.
        self.assertNoResponse(" ", to="#test_channel")

        _pr = conf.supybot.plugins.tell.you_have_mail()
        assert(_pr is not None)

    def testSkipTells(self):
        self.prefix = self._user2
        # Save ourselves a tell first.
        self.getMsg("tell foo hello world")

        self.prefix = self._user1
        self.assertNotError("skiptells")

        # If we have no tells, skip worked
        self.assertNoResponse(" ", to="#test_channel")

    def testDelayTells(self):
        self.prefix = self._user2
        # Save ourselves a tell first.
        self.getMsg("tell foo hello world")

        self.prefix = self._user1
        self.assertNotError("delaytells 1 hour")

        # If we have no tells, delay worked.
        self.assertNoResponse(" ", to="#test_channel")

    def testTellRefresh(self):
        _m = conf.supybot.plugins.tell.tell_refresh()
        assert(_m is not None)
        self.assertResponse("tellrefresh", _m.format(**{'count': 0}))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
