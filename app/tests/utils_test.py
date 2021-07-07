import random

import string


def get_random_string(length: int):
    letters = string.ascii_uppercase
    return "".join(random.choice(letters) for _ in range(length))
