-- grain: one row per report month; months = 1 keeps single-month differences (August covers two)
select cast(substr(period_end, 1, 4) as integer) as year,
       cast(substr(period_end, 6, 2) as integer) as month,
       packs
from monthly_packs
where months = 1
