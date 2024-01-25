from datetime import timedelta

CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TIMEZONE = 'UTC'
CELERYBEAT_SCHEDULE = {
    'auto_return_books': {
        'task': 'app.tasks.auto_return_books',
        'schedule': timedelta(minutes=1),  # Adjust the schedule as needed
    },
}
