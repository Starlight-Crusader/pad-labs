from django.db import models
from django.contrib.postgres.fields import ArrayField
import random
import string
import os
import subprocess


def get_docker_container_ip():
    ip = subprocess.check_output(['hostname', '-I']).decode('utf-8').strip()
    return ip


class GameLobby(models.Model):

    def generate_identifier():
        return ''.join(random.choices(str.lower(string.hexdigits), k=8))

    identifier = models.CharField(max_length=8, unique=True, default=generate_identifier)
    connect_url = models.CharField(max_length=128, blank=True)
    
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

    rating = models.IntegerField(blank=True)

    def save(self, *args, **kwargs):
        service_ip = get_docker_container_ip()
        service_port = os.getenv('PORT')

        # self.connect_url = f"ws://{service_ip}:{service_port}/lobby/{self.identifier}"
        self.connect_url = f"ws://localhost:{service_port}/lobby/{self.identifier}"

        super(GameLobby, self).save(*args, **kwargs)

    def __str__(self):
        return f"Lobby #{self.identifier}: {len(self.players)} players + {len(self.spectators)} spectators"