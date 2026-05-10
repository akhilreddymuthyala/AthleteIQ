from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import PredictionRoom, Prediction, DynamicPrediction, Match, Announcement, RoomMessage


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model  = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class RoomForm(forms.ModelForm):
    class Meta:
        model   = PredictionRoom
        fields  = ['name', 'description', 'room_type']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class JoinRoomForm(forms.Form):
    invite_code = forms.CharField(
        max_length=12,
        label='Invite code',
        widget=forms.TextInput(attrs={'placeholder': 'Enter 12-character code'})
    )


class PredictionForm(forms.ModelForm):
    class Meta:
        model  = Prediction
        fields = ['predicted_winner']

    def __init__(self, match, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['predicted_winner'] = forms.ChoiceField(
            choices=[
                (match.team_a, match.team_a),
                (match.team_b, match.team_b),
            ],
            label='Pick the winner',
            widget=forms.RadioSelect,
        )


class DynamicPredictionForm(forms.ModelForm):
    class Meta:
        model   = DynamicPrediction
        fields  = ['prediction_value']
        widgets = {
            'prediction_value': forms.TextInput(attrs={
                'placeholder': 'e.g. 12  or  2 wickets',
                'autofocus': True,
            })
        }
        labels = {'prediction_value': 'Your prediction'}


class MatchForm(forms.ModelForm):
    class Meta:
        model  = Match
        fields = ['league', 'team_a', 'team_b', 'scheduled_at']
        widgets = {
            'scheduled_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'team_a': forms.TextInput(attrs={'placeholder': 'e.g. Mumbai Indians'}),
            'team_b': forms.TextInput(attrs={'placeholder': 'e.g. Chennai Super Kings'}),
        }
        labels = {
            'team_a': 'Team A',
            'team_b': 'Team B',
            'scheduled_at': 'Match date & time',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['scheduled_at'].input_formats = ['%Y-%m-%dT%H:%M']


class ResultForm(forms.Form):
    winner = forms.ChoiceField(choices=[], widget=forms.RadioSelect, label='Who won?')

    def __init__(self, match, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['winner'].choices = [
            (match.team_a, match.team_a),
            (match.team_b, match.team_b),
        ]


# ── New forms ──────────────────────────────────────────────────────────────────

class MessageForm(forms.ModelForm):
    class Meta:
        model   = RoomMessage
        fields  = ['text']
        widgets = {
            'text': forms.TextInput(attrs={
                'placeholder': 'Type a message…',
                'autocomplete': 'off',
            })
        }
        labels = {'text': ''}


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model  = Announcement
        fields = ['message', 'type', 'lock_at']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g. Predict runs in this over',
            }),
            'lock_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }
        labels = {
            'message': 'Challenge description',
            'lock_at': 'Predictions close at',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lock_at'].input_formats = ['%Y-%m-%dT%H:%M']


class OutcomeForm(forms.Form):
    correct_outcome = forms.CharField(
        max_length=100,
        label='Correct answer',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. 8'})
    )