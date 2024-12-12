import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dogs.settings')

app = Celery('dogs')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.update(task_acks_late=True, task_reject_on_worker_lost=True)
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
