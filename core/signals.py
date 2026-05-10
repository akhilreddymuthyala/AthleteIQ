"""
Signals:
1. score_match       — fires when Match is saved as finished (Phase 3, unchanged)
2. notify_announcement — fires when new Announcement is created → calls n8n webhook
3. score_announcement  — fires when Announcement gets correct_outcome set → scores + calls n8n result webhook
"""

import json
import urllib.request
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from .models import Match, Prediction, Points, Announcement, DynamicPrediction

CORRECT_BASE = 10
STREAK_BONUS = 2

# ── n8n webhook URLs (set in settings.py / .env) ──────────────────────────────
# N8N_ANNOUNCEMENT_WEBHOOK  — n8n listens, fans out to members
# N8N_RESULT_WEBHOOK        — n8n listens, broadcasts result summary


# In core/signals.py — replace call_n8n function with this:

def call_n8n(url, payload):
    """Fire-and-forget POST to n8n webhook."""
    if not url:
        print("[n8n] No webhook URL configured — skipping")
        return
    try:
        data = json.dumps(payload).encode('utf-8')
        req  = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[n8n] ✅ Webhook fired → {url} → {resp.status}")
    except Exception as e:
        print(f"[n8n] ❌ Webhook failed → {url} → {e}")


# ── Phase 3: Match scoring ─────────────────────────────────────────────────────

@receiver(post_save, sender=Match)
def score_match(sender, instance, **kwargs):
    match = instance
    if match.status != 'finished' or not match.winner or match.scored:
        return

    predictions = Prediction.objects.filter(match=match).select_related('user', 'room')

    for pred in predictions:
        is_correct = (pred.predicted_winner == match.winner)
        pred.result = 'correct' if is_correct else 'incorrect'
        pred.save(update_fields=['result'])

        points_row, _ = Points.objects.get_or_create(user=pred.user, room=pred.room)
        points_row.total_predictions += 1

        if is_correct:
            points_row.streak              += 1
            points_row.correct_predictions += 1
            earned = CORRECT_BASE + (STREAK_BONUS * (points_row.streak - 1))
            points_row.total_points += earned
            if points_row.streak > points_row.best_streak:
                points_row.best_streak = points_row.streak
        else:
            points_row.streak = 0

        points_row.save()

    Match.objects.filter(pk=match.pk).update(scored=True)


# ── Phase 4: Announcement push ─────────────────────────────────────────────────

@receiver(post_save, sender=Announcement)
def handle_announcement(sender, instance, created, **kwargs):
    ann = instance

    # 1. New announcement → notify all room members via n8n
    if created and not ann.n8n_notified:
        members = list(ann.room.members.values_list('username', flat=True))
        payload = {
            'event':       'new_announcement',
            'room':        ann.room.name,
            'message':     ann.message,
            'type':        ann.type,
            'lock_at':     ann.lock_at.isoformat(),
            'members':     members,
            'announcement_id': ann.pk,
        }
        call_n8n(getattr(settings, 'N8N_ANNOUNCEMENT_WEBHOOK', ''), payload)
        Announcement.objects.filter(pk=ann.pk).update(n8n_notified=True)

    # 2. Outcome set + not yet scored → score dynamic predictions + broadcast result
    if ann.correct_outcome and not ann.scored:
        _score_announcement(ann)


def _score_announcement(ann):
    """
    Scoring rules for dynamic predictions:
      Exact match  → +10 pts
      Close guess  → +5 pts  (numeric predictions within ±2)
      Incorrect    → 0 pts
    """
    predictions = DynamicPrediction.objects.filter(
        announcement=ann
    ).select_related('user')

    results_summary = []

    for pred in predictions:
        correct = ann.correct_outcome.strip()
        guessed = pred.prediction_value.strip()

        # Try numeric close-guess logic
        try:
            correct_num = float(correct)
            guessed_num = float(guessed)
            diff = abs(correct_num - guessed_num)

            if diff == 0:
                pred.result       = DynamicPrediction.Result.EXACT
                pred.points_earned = 10
            elif diff <= 2:
                pred.result        = DynamicPrediction.Result.CLOSE
                pred.points_earned = 5
            else:
                pred.result        = DynamicPrediction.Result.INCORRECT
                pred.points_earned = 0
        except ValueError:
            # Non-numeric: exact string match only
            if guessed.lower() == correct.lower():
                pred.result        = DynamicPrediction.Result.EXACT
                pred.points_earned = 10
            else:
                pred.result        = DynamicPrediction.Result.INCORRECT
                pred.points_earned = 0

        pred.save(update_fields=['result', 'points_earned'])

        # Add to room Points
        if pred.points_earned > 0:
            points_row, _ = Points.objects.get_or_create(
                user=pred.user,
                room=ann.room,
            )
            points_row.total_points += pred.points_earned
            points_row.save(update_fields=['total_points'])

        results_summary.append({
            'user':   pred.user.username,
            'guess':  guessed,
            'result': pred.result,
            'points': pred.points_earned,
        })

    # Mark scored
    Announcement.objects.filter(pk=ann.pk).update(scored=True)

    # Broadcast result to n8n
    payload = {
        'event':           'announcement_result',
        'room':            ann.room.name,
        'message':         ann.message,
        'correct_outcome': ann.correct_outcome,
        'results':         results_summary,
    }
    call_n8n(getattr(settings, 'N8N_RESULT_WEBHOOK', ''), payload)