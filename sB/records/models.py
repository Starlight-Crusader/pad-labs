from django.db import models
from django.contrib.postgres.fields import ArrayField


class GameRecord(models.Model):
    player1 = models.IntegerField()
    player2 = models.IntegerField()

    moves = ArrayField(models.CharField(max_length=10))

    finished_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Game between player #{self.player1} and player #{self.player2} finished on {self.finished_at}"
