MemoServ replacement with extra features.

Requires SQLAlchemy

# Development Guide
- http://doc.supybot.aperio.fr/en/latest/
- Install limonira
- Clone the plugin in its folder
- Use the plugin-test script for proper testing
- Add yourself to the contributors area

## TODO
- Add more tests (TDD not required). FULL TEST CONVERAGE OF COMMANDS AND EMITTERS REQUIRED!!!
- Refactor out all of the ORM into its own module. Provide a library for the commands. Look how ProgVal does it: https://github.com/ProgVal/Limnoria/tree/master/plugins/Todo

### Old Use Cases
- When you PM the bot using !tell, it saves it as a private emit. Use Limnoria's channel DB system for this?

### Existing commands
- !tell - add a new tell (either private or public)
- !skiptells - mark all pending tells as delievered
- !delaytells - set an expiration date on the in memory object (maybe we should move this off to the DB too?). Use this expiration date to withold emitting the tell
- !telrefresh - dumps RAM and then re-fetches everything from the DB and reloads. (use this if you manually change records in the DB outside of the bot. Or if delay tells gets messed up) Its basically a resync with DB command.

## Things that should be implemented
- Import all UNREAD tells in the DB into memory on startup. Keep them synced with the DB. Is there a way to override CRUD operations in SQLAlchemy to keep our own in memory copy?
- Allow the format of emitted tells to be configured. Take advantage of limnoria's configuration system to do this
