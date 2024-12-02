import random


def random_logo_name(request):
    names = ["kok nangis", "spobob", "spongebob fandom", "fandomnya spongebob", "aaaaaaaa", "spogbob fansom"]
    random_name = random.choice(names)
    return {'random_logo_name': random_name}