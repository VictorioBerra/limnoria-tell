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

import supybot.conf as conf
import supybot.registry as registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Tell')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Tell', True)


Tell = conf.registerPlugin('Tell')

conf.registerGlobalValue(
    conf.supybot.plugins.Tell,
    'you_have_mail',
    registry.String(
        '{to}, you have {pub_count} tell{plural}:',
        """Top level message for Tell; you have x messages"""))
conf.registerGlobalValue(
    conf.supybot.plugins.Tell,
    'you_have_private_mail',
    registry.String(
        '{to}, you have {priv_count} private tell{plural}:',
        """Top level message for Tell; you have x private messages"""))
conf.registerGlobalValue(
    conf.supybot.plugins.Tell,
    'tell_message',
    registry.String(
        '{time_ago} from {from}: {content}',
        """Top level message for Tell; you have x private messages"""))
conf.registerGlobalValue(
    conf.supybot.plugins.Tell,
    'tell_refresh',
    registry.String(
        '{count} have been reloaded from the database.',
        """Message to reply when reloading Tells from Database"""))

conf.registerGlobalValue(
    conf.supybot.plugins.Tell,
    'tell_skip',
    registry.String(
        'Skipping {count} tells.',
        """Message to reply when skipping tells"""))
