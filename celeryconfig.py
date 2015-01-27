import datetime

BROKER_URL = 'redis://'
CELERY_RESULT_BACKEND = 'redis'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERYBEAT_SCHEDULE = {
    'tick-every-5-minutes': {
        'task': 'tasks.tick',
        'schedule': datetime.timedelta(minutes=5),
    }
}
