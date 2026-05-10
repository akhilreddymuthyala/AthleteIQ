import uuid
from django.db import models
from django.contrib.auth.models import User


# ── Phase 1 ────────────────────────────────────────────────────────────────────

class Sport(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class League(models.Model):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='leagues')
    name  = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.name} ({self.sport.name})"


class Match(models.Model):

    class Status(models.TextChoices):
        UPCOMING  = 'upcoming',  'Upcoming'
        LIVE      = 'live',      'Live'
        FINISHED  = 'finished',  'Finished'
        CANCELLED = 'cancelled', 'Cancelled'

    league       = models.ForeignKey(League, on_delete=models.CASCADE, related_name='matches')
    room         = models.ForeignKey(                          # ← NEW in Phase 5
        'PredictionRoom',
        on_delete=models.CASCADE,
        related_name='matches',
        null=True, blank=True,
        help_text='Room this match belongs to. Leave blank for global matches.'
    )
    team_a       = models.CharField(max_length=100)
    team_b       = models.CharField(max_length=100)
    scheduled_at = models.DateTimeField()
    status       = models.CharField(max_length=20, choices=Status.choices, default=Status.UPCOMING)
    winner       = models.CharField(max_length=100, blank=True, null=True)
    scored       = models.BooleanField(default=False)

    class Meta:
        ordering = ['-scheduled_at']

    def __str__(self):
        return f"{self.team_a} vs {self.team_b} [{self.get_status_display()}]"

    def is_locked(self):
        return self.status != self.Status.UPCOMING

    def prediction_count(self):
        return self.predictions.count()


# ── Phase 2 ────────────────────────────────────────────────────────────────────

class PredictionRoom(models.Model):

    class RoomType(models.TextChoices):
        PUBLIC  = 'public',  'Public'
        PRIVATE = 'private', 'Private'

    name        = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    room_type   = models.CharField(max_length=10, choices=RoomType.choices, default=RoomType.PUBLIC)
    invite_code = models.CharField(max_length=12, unique=True, blank=True)
    admin       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_rooms')
    members     = models.ManyToManyField(User, related_name='joined_rooms', blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = uuid.uuid4().hex[:12].upper()
        super().save(*args, **kwargs)

    def is_member(self, user):
        return self.members.filter(pk=user.pk).exists()


class Prediction(models.Model):

    class Result(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        CORRECT   = 'correct',   'Correct'
        INCORRECT = 'incorrect', 'Incorrect'

    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions')
    room             = models.ForeignKey(PredictionRoom, on_delete=models.CASCADE, related_name='predictions')
    match            = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='predictions')
    predicted_winner = models.CharField(max_length=100)
    result           = models.CharField(max_length=10, choices=Result.choices, default=Result.PENDING)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'match', 'room']

    def __str__(self):
        return f"{self.user.username} → {self.predicted_winner} [{self.get_result_display()}]"


# ── Phase 3 ────────────────────────────────────────────────────────────────────

class Points(models.Model):
    user                = models.ForeignKey(User, on_delete=models.CASCADE, related_name='points')
    room                = models.ForeignKey(PredictionRoom, on_delete=models.CASCADE, related_name='points')
    total_points        = models.IntegerField(default=0)
    streak              = models.IntegerField(default=0)
    best_streak         = models.IntegerField(default=0)
    total_predictions   = models.IntegerField(default=0)
    correct_predictions = models.IntegerField(default=0)

    class Meta:
        unique_together = ['user', 'room']
        ordering        = ['-total_points', '-streak']

    def __str__(self):
        return f"{self.user.username} in {self.room.name}: {self.total_points} pts"

    @property
    def accuracy(self):
        if self.total_predictions == 0:
            return 0
        return round((self.correct_predictions / self.total_predictions) * 100)


# ── Phase 4 ────────────────────────────────────────────────────────────────────

class Announcement(models.Model):

    class AnnouncementType(models.TextChoices):
        RUNS    = 'runs',    'Runs in over'
        WICKETS = 'wickets', 'Wickets'
        CUSTOM  = 'custom',  'Custom'

    room            = models.ForeignKey(PredictionRoom, on_delete=models.CASCADE, related_name='announcements')
    message         = models.TextField()
    type            = models.CharField(max_length=20, choices=AnnouncementType.choices, default=AnnouncementType.CUSTOM)
    created_by      = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at      = models.DateTimeField(auto_now_add=True)
    lock_at         = models.DateTimeField()
    is_locked       = models.BooleanField(default=False)
    correct_outcome = models.CharField(max_length=100, blank=True, null=True)
    scored          = models.BooleanField(default=False)
    n8n_notified    = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.room.name}] {self.message[:50]}"


class DynamicPrediction(models.Model):

    class Result(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        EXACT     = 'exact',     'Exact match'
        CLOSE     = 'close',     'Close guess'
        INCORRECT = 'incorrect', 'Incorrect'

    announcement     = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='predictions')
    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dynamic_predictions')
    prediction_value = models.CharField(max_length=100)
    result           = models.CharField(max_length=10, choices=Result.choices, default=Result.PENDING)
    points_earned    = models.IntegerField(default=0)
    submitted_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['announcement', 'user']

    def __str__(self):
        return f"{self.user.username}: {self.prediction_value} [{self.get_result_display()}]"

# Add this class at the very end of models.py

class RoomMessage(models.Model):
    room       = models.ForeignKey(PredictionRoom, on_delete=models.CASCADE, related_name='messages')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_messages')
    text       = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} in {self.room.name}: {self.text[:40]}"    