def get_previous_interval(intervals, target):
    try:
        # Найти индекс заданного значения
        index = intervals.index(target)
        # Вернуть предыдущее значение, если оно существует
        return intervals[index - 1] if index > 0 else target
    except ValueError:
        # Если значение не найдено в массиве, вернуть None
        return target