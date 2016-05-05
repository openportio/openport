import random
import string

def get_token(size=16, chars=string.digits + string.ascii_letters):
    return ''.join(random.choice(chars) for x in range(size))