# Protivnik: vozi na nasumične tačke po celom stolu (isti sto = ista putanja: seme je u podešavanju protivnika).
import random
from gambit import *

START = (250, 1000, 0)

while True:
    goto(random.randint(400, 2600), random.randint(350, 1650), speed=random.choice((300, 500, 700)))
    wait(random.random() * 2)
