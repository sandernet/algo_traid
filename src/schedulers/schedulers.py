from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger


from config import Config
config = Config()


# Функция для настройки периодического запроса
def start_scheduler(func):
    scheduler = AsyncIOScheduler()
    # scheduler.add_job(send_message, CronTrigger(hour=8, minute=45), kwargs={'message': 'scheduler', 'warehouseIDs': ''})  
    scheduler.add_job(func, IntervalTrigger(minutes=3), kwargs={})  
    # scheduler.add_job(func, IntervalTrigger(minutes=config.TIMEFRAME), kwargs={"Получаем предсказания"})  
    scheduler.start()