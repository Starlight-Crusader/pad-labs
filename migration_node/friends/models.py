from django.db import models
from users.models import User


class FriendRequest(models.Model):
    STATUS_CHOICES = [
        (0, 'Pending'),
        (1, 'Accepted'),
        (2, 'Rejected'),
    ]

    sender = models.ForeignKey(User, related_name='sent_friend_requests', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_friend_requests', on_delete=models.CASCADE)
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)

    class Meta:
        unique_together = ('sender', 'receiver')  # Prevent duplicate friend requests

    def __str__(self):
        return f"FriendRequest from {self.sender} to {self.receiver} - Status: {self.get_status_display()}"