from config import Config
import sqlalchemy
import sqlalchemy.orm
from woodwind.models import Entry
from woodwind import util

engine = sqlalchemy.create_engine(Config.SQLALCHEMY_DATABASE_URI)
Session = sqlalchemy.orm.sessionmaker(bind=engine)

try:
    engine.execute('alter table entry add column content_cleaned text')
except:
    pass

try:
    session = Session()

    for entry in session.query(Entry).all():
        print('processing', entry.id)
        entry.content_cleaned = util.clean(entry.content)

    session.commit()
except:
    session.rollback()
    raise
finally:
    session.close()
