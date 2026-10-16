import calendar
from datetime import date

import holidays


def working_days(year: int, month: int, saturdays: bool = False) -> int:
    """Weekdays (and Saturdays if asked) of a month, less Spain's national holidays.

    Regional and local holidays are not modelled.
    """
    national = holidays.Spain(years=year)
    last = 6 if saturdays else 5
    return sum(1 for d in range(1, calendar.monthrange(year, month)[1] + 1)
               if date(year, month, d).weekday() < last and date(year, month, d) not in national)
