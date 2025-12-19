# src/backtester/reports/serializers.py
def serialize_order(order):
    return {
        "id": order.id,
        "type": order.order_type.name,
        "status": order.status.name,
        "price": float(order.price),
        "volume": float(order.volume),
        "created_bar": order.created_bar,
        "close_bar": order.close_bar,
        "meta": order.meta or {},
    }

def serialize_position(position):
    return {
        "id": position.id,
        "symbol": position.symbol,
        "direction": position.direction.name,
        "status": position.status.name,
        "opened_bar": position.bar_opened,
        "closed_bar": position.bar_closed,
        "avg_entry_price": float(position.avg_entry_price) if position.avg_entry_price else None,
        "realized_pnl": float(position.realized_pnl),
        "orders": [serialize_order(o) for o in position.orders],
    }

def serialize_positions(positions: dict):
    return [serialize_position(p) for p in positions.values()]
