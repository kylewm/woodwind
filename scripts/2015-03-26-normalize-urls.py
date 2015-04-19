from config import Config
from woodwind import util
from woodwind.models import Feed
import requests
import sqlalchemy
import sqlalchemy.orm
import sys

engine = sqlalchemy.create_engine(Config.SQLALCHEMY_DATABASE_URI)
Session = sqlalchemy.orm.sessionmaker(bind=engine)

def follow_redirects():
    try:
        session = Session()
        feeds = session.query(Feed).all()
        for feed in feeds:
            print('fetching', feed.feed)
            try:
                r = requests.head(feed.feed, allow_redirects=True)
                if feed.feed != r.url:
                    print('urls differ', feed.feed, r.url)
                    feed.feed = r.url
            except:
                print('error', sys.exc_info()[0])
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def dedupe():
    try:
        session = Session()
        feeds = session.query(Feed).order_by(Feed.id).all()

        removed = set()
        
        for f1 in feeds:
            if f1.id in removed:
                continue
            
            for f2 in feeds:
                if f2.id in removed:
                    continue
                
                if f1.id < f2.id and f1.feed == f2.feed:
                    print('dedupe', f1.feed, f1.id, f2.id)
                    f1.users += f2.users
                    f2.users.clear()
                    removed.add(f2.id)
                    session.delete(f2)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
        
dedupe()
