from enum import Enum

class Position_Status(Enum):
    ACTIVE = "active"           #активная позиция
    TAKEN_PART = "part_taken"   #финальный статус, когда позиция была исполнена частично
    TAKEN_FULL = "taken_full"   #финальный статус, когда позиция была исполнена полностью
    STOPPED = "stopped"         #финальный статус, когда позиция была остановлена по стоп-лоссу в минусе
    CANCELED = "cancelled"      #финальный статус, когда позиция была отменена (профит может быть как положительный так и отрицательный)
    NONE = "none"               #начальный статус, когда позиция не создана
    CREATED = "created"         #начальный статус, когда позиция создана


class OrderType(Enum):
    ENTRY = "entry"     # вход в позицию
    TAKE_PROFIT = "tp"  # тейк-профит
    STOP_LOSS = "sl"    # стоп-лосс
    CLOSE = "close"     # закрытие позиции
    TRAILING_STOP = "trailing_stop" # трейлинг-стоп
    LIMIT = "limit"   # лимитный ордер
    MARKET = "market"  # рыночный ордер


class OrderStatus(Enum):
    ACTIVE = "active"
    FILLED = "filled"
    CANCELLED = "cancelled"
    PARTIAL = "partial"

# направление позиции
class Direction(Enum):
    LONG = "long"
    SHORT = "short"
    
    

# ==========================
# Signal Перечисления
# ==========================
class SignalType(Enum):
    ENTRY = "entry"
    EXIT = "exit"
    HEDGE_OPEN = "hedge_open"
    HEDGE_CLOSE = "hedge_close"
    UPDATE         = "update" # изменить позицию (SL, TP)    
    CANCEL = "cancel" # закрыть позицию  по рынку
    NO_SIGNAL = "no_signal" # отсутствие сигнала


class SignalSource(Enum):
    STRATEGY = "strategy"
    ALS = "als"
    MANUAL = "manual"