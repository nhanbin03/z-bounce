"""
SQL query
"""

MATCHED_QUERY = """
  select m.datetime, m.tickersymbol, m.price, v.quantity
  from quote.matched m
  join quote.futurecontractcode fc on date(m.datetime) = fc.datetime and fc.tickersymbol = m.tickersymbol
  left join quote.total v on m.datetime = v.datetime and m.tickersymbol = v.tickersymbol
  where fc.futurecode = %s and m.datetime between %s and %s and
        ((EXTRACT(HOUR FROM m.datetime) >= 9 AND EXTRACT(HOUR FROM m.datetime) < 14)
        OR (EXTRACT(HOUR FROM m.datetime) = 14 AND EXTRACT(MINUTE FROM m.datetime) <= 30))
  order by m.datetime
"""

CLOSE_QUERY = """
  select c.datetime, c.tickersymbol, c.price
  from quote.close c
  join quote.futurecontractcode fc on c.datetime = fc.datetime and fc.tickersymbol = c.tickersymbol
  where fc.futurecode = %s and c.datetime between %s and %s
  order by c.datetime
"""
