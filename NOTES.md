Clear out orphaned feeds

```
delete from entry_to_reply_context where entry_id in (select id from entry where feed_id in (select id from feed where not exists (select * from users_to_feeds where feed_id = feed.id)));
delete from entry_to_reply_context where context_id in (select id from entry where feed_id in (select id from feed where not exists (select * from users_to_feeds where feed_id = feed.id)));
delete from entry where feed_id in (select id from feed where not exists (select * from users_to_feeds where feed_id = feed.id));
delete from feed where not exists (select * from users_to_feeds where feed_id = feed.id);
```
