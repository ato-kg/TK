import random


def random_logo_name(request):
    names = ["spongebob fandom"]
    random_name = random.choice(names)
    return {'random_logo_name': random_name}