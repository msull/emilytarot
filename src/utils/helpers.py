import random
from datetime import datetime
from string import ascii_lowercase


def date_id(now=None):
    now = now or datetime.utcnow()
    return now.strftime("%Y%m%d%H") + "".join(random.choices(ascii_lowercase, k=6))
