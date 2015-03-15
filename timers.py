from uwsgidecorators import timer
from woodwind import tasks


@timer(300)
def tick(signum=None):
    tasks.q.enqueue(tasks.tick)
