from django.contrib import admin
from .models import Sport, League, Match, PredictionRoom, Prediction, Points, Announcement, DynamicPrediction


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display  = ['name']
    search_fields = ['name']


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display  = ['name', 'sport']
    list_filter   = ['sport']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display  = ['__str__', 'scheduled_at', 'status', 'winner', 'scored']
    list_filter   = ['status', 'league__sport']
    list_editable = ['status', 'winner']
    readonly_fields = ['scored']
    fieldsets = (
        ('Match details', {'fields': ('league', 'team_a', 'team_b', 'scheduled_at')}),
        ('Result', {
            'fields': ('status', 'winner', 'scored'),
            'description': 'Set Status=Finished + Winner → Save. Scoring is automatic.',
        }),
    )


@admin.register(PredictionRoom)
class PredictionRoomAdmin(admin.ModelAdmin):
    list_display    = ['name', 'room_type', 'admin', 'invite_code']
    readonly_fields = ['invite_code']


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ['user', 'match', 'room', 'predicted_winner', 'result']
    list_filter  = ['result', 'room']


@admin.register(Points)
class PointsAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'total_points', 'streak', 'best_streak',
                    'correct_predictions', 'total_predictions']
    list_filter  = ['room']
    ordering     = ['-total_points']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display  = ['__str__', 'room', 'type', 'lock_at', 'is_locked', 'scored', 'correct_outcome']
    list_filter   = ['room', 'type', 'is_locked', 'scored']
    readonly_fields = ['scored', 'n8n_notified']
    fieldsets = (
        ('Challenge', {
            'fields': ('room', 'message', 'type', 'lock_at'),
            'description': 'Create a challenge. Saving this immediately notifies room members via n8n.',
        }),
        ('Lock & Result', {
            'fields': ('is_locked', 'correct_outcome', 'scored', 'n8n_notified'),
            'description': (
                '1. Tick "Is locked" when the event ends to stop new predictions. '
                '2. Fill "Correct outcome" (e.g. "8") → Save. Scoring + broadcast runs automatically.'
            ),
        }),
    )


@admin.register(DynamicPrediction)
class DynamicPredictionAdmin(admin.ModelAdmin):
    list_display = ['user', 'announcement', 'prediction_value', 'result', 'points_earned']
    list_filter  = ['result', 'announcement__room']