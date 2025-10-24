from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.triggers.cron import CronTrigger
import pytz

import src.config.config as config


# Функция для настройки периодического запроса
def start_scheduler(func):
    
    cfg = config.get_config()
    
    # Настройки планировщика из config.json
    hour =  cfg["scheduler"]["hour"] #hour = 8,
    minute = cfg["scheduler"]["minute"] #0,
    second = cfg["scheduler"]["second"] #15,
    timezone = cfg["scheduler"]["timezone"] #"Asia/Irkutsk"
    
    # Часовой пояс Иркутска
    tz = pytz.timezone(timezone)
    
    # Создаём scheduler с AsyncIOExecutor
    scheduler = AsyncIOScheduler()
    scheduler.add_job(func, CronTrigger(hour=hour, minute=minute, second=second, timezone=tz))
    scheduler.start()
