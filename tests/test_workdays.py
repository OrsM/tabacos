from tabacos.workdays import working_days


def test_weekdays_less_national_holidays():
    assert working_days(2025, 1) == 21          # 23 weekdays; 1 Jan (Wed) and 6 Jan (Mon) are holidays
    assert working_days(2024, 2) == 21          # leap February, 29 days, no holiday
    assert working_days(2025, 12) == 21         # 8 Dec (Mon) and 25 Dec (Thu); 6 Dec is a Saturday


def test_counting_saturdays_too():
    assert working_days(2025, 1, saturdays=True) == 25      # + Saturdays 4, 11, 18, 25
