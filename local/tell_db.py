from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()


class TellDB(object):

    @staticmethod
    def commit_db():
        session.commit()

    # FromNick=msg.nick, ToNick=i, Content=message, Private=self.pm, Read=0,Timestamp=_dt
    @staticmethod
    def insert_tell(from_nick, to_nick, message, private, time):
        new_tell = TellRecord(FromNick=from_nick, ToNick=to_nick, Content=message, Private=private, Read=0,
                              Timestamp=time)
        session.add(new_tell)
        session.commit()

        # Return inserted id
        return new_tell.ID

    @staticmethod
    def query_unread():
        _d = session.query(TellRecord).filter(TellRecord.Read == 0).all()
        session.commit()
        return _d

    @staticmethod
    def update_read(record_id):
        stmt = TellRecord.__table__.update().where(TellRecord.ID == record_id).values(Read=True)
        session.execute(stmt)
        session.commit()


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


# Create engine for Database, Mysql, sqlite, etc
engine = create_engine(os.environ['TELL_CONNECTION_STRING'])
# See if we need to create a new schema.
if 'IRC_BOT_DEV' in os.environ and os.environ['IRC_BOT_DEV'] == "1":
    Base.metadata.create_all(engine)

Base.metadata.bind = engine

# Create session
DBSession = sessionmaker(bind=engine)
session = DBSession()

