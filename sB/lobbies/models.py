from django.db import models
from django.contrib.postgres.fields import ArrayField
import random
import string


class GameLobby(models.Model):

    def generate_identifier():
        return ''.join(random.choices(string.hexdigits, k=8))

    identifier = models.CharField(max_length=8, unique=True, default=generate_identifier)
    
    # Array of integers for player IDs
    players = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True
    )
    
    # Array of integers for spectator IDs
    spectators = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True
    )

    def __str__(self):
        return f"Lobby #{self.identifier}: {len(self.players)} players + {len(self.spectators)} spectators"