from django.db import models
from django.contrib.postgres.fields import ArrayField


class GameRecord(models.Model):
    white_player = models.CharField(max_length=150)
    black_player = models.CharField(max_length=150)

    moves = ArrayField(models.CharField(max_length=10))

    finished_at = models.DateTimeField()

    def __str__(self):
        return f"Game between player #{self.white_player} and player #{self.black_player} finished on {self.finished_at}"
