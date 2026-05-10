from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse

from .forms import (
    RegisterForm, RoomForm, JoinRoomForm,
    PredictionForm, DynamicPredictionForm,
    MatchForm, ResultForm,
    MessageForm, AnnouncementForm, OutcomeForm,
)
from .models import (
    Match, PredictionRoom, Prediction, Points,
    Announcement, DynamicPrediction, RoomMessage,
)


# ── Auth ───────────────────────────────────────────────────────────────────────

def home(request):
    upcoming = Match.objects.filter(status='upcoming').select_related('league__sport')[:10]
    live     = Match.objects.filter(status='live').select_related('league__sport')
    finished = Match.objects.filter(status='finished').select_related('league__sport')[:5]
    return render(request, 'core/home.html', {
        'upcoming': upcoming,
        'live':     live,
        'finished': finished,
    })


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome, {user.username}!")
        return redirect('home')
    return render(request, 'core/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('home')
    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# ── Rooms ──────────────────────────────────────────────────────────────────────

@login_required
def rooms_list(request):
    public_rooms = PredictionRoom.objects.filter(room_type='public').select_related('admin')
    my_rooms     = request.user.joined_rooms.all().select_related('admin')
    return render(request, 'core/rooms.html', {
        'public_rooms': public_rooms,
        'my_rooms':     my_rooms,
    })


@login_required
def room_create(request):
    form = RoomForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        room = form.save(commit=False)
        room.admin = request.user
        room.save()
        room.members.add(request.user)
        messages.success(request, f'Room "{room.name}" created!')
        return redirect('room_detail', pk=room.pk)
    return render(request, 'core/room_create.html', {'form': form})


@login_required
def room_delete(request, pk):
    room = get_object_or_404(PredictionRoom, pk=pk)
    if room.admin != request.user:
        messages.error(request, 'Only the room admin can delete this room.')
        return redirect('room_detail', pk=pk)
    if request.method == 'POST':
        room_name = room.name
        room.delete()
        messages.success(request, f'Room "{room_name}" deleted.')
        return redirect('rooms_list')
    return render(request, 'core/room_delete_confirm.html', {'room': room})


@login_required
def room_detail(request, pk):
    room = get_object_or_404(PredictionRoom, pk=pk)

    if room.room_type == 'private' and not room.is_member(request.user):
        messages.error(request, 'This is a private room. You need an invite code.')
        return redirect('room_join')

    if room.room_type == 'public' and not room.is_member(request.user):
        room.members.add(request.user)

    open_matches     = Match.objects.filter(room=room, status='upcoming').select_related('league')
    live_matches     = Match.objects.filter(room=room, status='live').select_related('league')
    finished_matches = Match.objects.filter(room=room, status='finished').select_related('league')[:5]

    user_predictions = Prediction.objects.filter(
        user=request.user, room=room
    ).values_list('match_id', flat=True)

    user_points = Points.objects.filter(user=request.user, room=room).first()

    announcements = Announcement.objects.filter(room=room).prefetch_related('predictions')

    user_dyn_predictions = DynamicPrediction.objects.filter(
        user=request.user, announcement__room=room,
    ).values_list('announcement_id', flat=True)

    # Chat
    chat_messages = RoomMessage.objects.filter(room=room).select_related('user').order_by('created_at')
    chat_form     = MessageForm()

    is_admin = (room.admin == request.user)

    # Handle chat POST
    if request.method == 'POST':
        chat_form = MessageForm(request.POST)
        if chat_form.is_valid():
            msg = chat_form.save(commit=False)
            msg.room = room
            msg.user = request.user
            msg.save()
            return redirect('room_detail', pk=pk)

    return render(request, 'core/room_detail.html', {
        'room':                 room,
        'open_matches':         open_matches,
        'live_matches':         live_matches,
        'finished_matches':     finished_matches,
        'user_predictions':     user_predictions,
        'members':              room.members.all(),
        'user_points':          user_points,
        'announcements':        announcements,
        'user_dyn_predictions': user_dyn_predictions,
        'chat_messages':        chat_messages,
        'chat_form':            chat_form,
        'is_admin':             is_admin,
    })


@login_required
def room_join(request):
    form = JoinRoomForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        code = form.cleaned_data['invite_code'].upper()
        try:
            room = PredictionRoom.objects.get(invite_code=code)
            room.members.add(request.user)
            messages.success(request, f'Joined "{room.name}" successfully!')
            return redirect('room_detail', pk=room.pk)
        except PredictionRoom.DoesNotExist:
            messages.error(request, 'Invalid invite code.')
    return render(request, 'core/room_join.html', {'form': form})


@login_required
def transfer_admin(request, room_pk, user_pk):
    from django.contrib.auth.models import User
    room      = get_object_or_404(PredictionRoom, pk=room_pk)
    new_admin = get_object_or_404(User, pk=user_pk)

    if room.admin != request.user:
        messages.error(request, 'Only the current admin can transfer admin rights.')
        return redirect('room_detail', pk=room_pk)

    if not room.is_member(new_admin):
        messages.error(request, 'That user is not a member of this room.')
        return redirect('admin_dashboard', room_pk=room_pk)

    if request.method == 'POST':
        room.admin = new_admin
        room.save()
        messages.success(request, f'{new_admin.username} is now the room admin.')
        return redirect('room_detail', pk=room_pk)

    return render(request, 'core/transfer_admin_confirm.html', {
        'room':      room,
        'new_admin': new_admin,
    })


# ── Chat API (JSON polling) ────────────────────────────────────────────────────

@login_required
def chat_messages_json(request, room_pk):
    """Returns latest messages as JSON. Frontend polls this every 5s."""
    room = get_object_or_404(PredictionRoom, pk=room_pk)

    if not room.is_member(request.user):
        return JsonResponse({'error': 'not a member'}, status=403)

    since_id = request.GET.get('since', 0)
    msgs = RoomMessage.objects.filter(
        room=room, pk__gt=since_id
    ).select_related('user').order_by('created_at')

    data = [
        {
            'id':         m.pk,
            'username':   m.user.username,
            'text':       m.text,
            'time':       m.created_at.strftime('%H:%M'),
            'is_me':      m.user == request.user,
            'is_admin':   m.user == room.admin,
        }
        for m in msgs
    ]
    return JsonResponse({'messages': data})


@login_required
def chat_send(request, room_pk):
    """AJAX POST — sends a chat message, returns the new message as JSON."""
    room = get_object_or_404(PredictionRoom, pk=room_pk)

    if not room.is_member(request.user):
        return JsonResponse({'error': 'not a member'}, status=403)

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if not text:
            return JsonResponse({'error': 'empty'}, status=400)
        if len(text) > 500:
            return JsonResponse({'error': 'too long'}, status=400)

        msg = RoomMessage.objects.create(room=room, user=request.user, text=text)
        return JsonResponse({
            'id':       msg.pk,
            'username': msg.user.username,
            'text':     msg.text,
            'time':     msg.created_at.strftime('%H:%M'),
            'is_me':    True,
            'is_admin': msg.user == room.admin,
        })

    return JsonResponse({'error': 'method not allowed'}, status=405)


# ── Announcements (admin from app) ─────────────────────────────────────────────

@login_required
def announcement_create(request, room_pk):
    room = get_object_or_404(PredictionRoom, pk=room_pk)
    if room.admin != request.user:
        messages.error(request, 'Only the room admin can post challenges.')
        return redirect('announcement_list', room_pk=room_pk)

    form = AnnouncementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        ann = form.save(commit=False)
        ann.room       = room
        ann.created_by = request.user
        ann.save()   # signal fires n8n notification
        messages.success(request, 'Challenge posted! Members will be notified.')
        return redirect('announcement_list', room_pk=room_pk)

    return render(request, 'core/announcement_create.html', {
        'form': form,
        'room': room,
    })


@login_required
def announcement_lock(request, room_pk, ann_pk):
    room = get_object_or_404(PredictionRoom, pk=room_pk)
    ann  = get_object_or_404(Announcement, pk=ann_pk, room=room)

    if room.admin != request.user:
        messages.error(request, 'Only the room admin can lock challenges.')
        return redirect('announcement_list', room_pk=room_pk)

    if request.method == 'POST':
        ann.is_locked = True
        ann.save(update_fields=['is_locked'])
        messages.success(request, 'Challenge locked. No more predictions accepted.')

    return redirect('announcement_list', room_pk=room_pk)


@login_required
def announcement_set_outcome(request, room_pk, ann_pk):
    room = get_object_or_404(PredictionRoom, pk=room_pk)
    ann  = get_object_or_404(Announcement, pk=ann_pk, room=room)

    if room.admin != request.user:
        messages.error(request, 'Only the room admin can set the outcome.')
        return redirect('announcement_list', room_pk=room_pk)

    if ann.scored:
        messages.info(request, 'This challenge is already scored.')
        return redirect('announcement_list', room_pk=room_pk)

    form = OutcomeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        ann.correct_outcome = form.cleaned_data['correct_outcome']
        ann.is_locked       = True
        ann.save()   # signal fires scoring + n8n result broadcast
        messages.success(request, f'Outcome set to "{ann.correct_outcome}". Scoring complete!')
        return redirect('announcement_list', room_pk=room_pk)

    return render(request, 'core/announcement_set_outcome.html', {
        'form': form,
        'ann':  ann,
        'room': room,
    })


@login_required
def announcement_list(request, room_pk):
    room = get_object_or_404(PredictionRoom, pk=room_pk)

    if not room.is_member(request.user):
        messages.error(request, 'Access denied.')
        return redirect('rooms_list')

    announcements = Announcement.objects.filter(room=room).prefetch_related('predictions')
    user_preds    = DynamicPrediction.objects.filter(
        user=request.user, announcement__room=room
    ).select_related('announcement')
    user_pred_map = {dp.announcement_id: dp for dp in user_preds}
    is_admin      = room.admin == request.user

    return render(request, 'core/announcement_list.html', {
        'room':          room,
        'announcements': announcements,
        'user_pred_map': user_pred_map,
        'is_admin':      is_admin,
    })


# ── Predictions ────────────────────────────────────────────────────────────────

@login_required
def predict(request, room_pk, match_pk):
    room  = get_object_or_404(PredictionRoom, pk=room_pk)
    match = get_object_or_404(Match, pk=match_pk)

    if not room.is_member(request.user):
        messages.error(request, 'You are not a member of this room.')
        return redirect('rooms_list')

    if match.is_locked():
        messages.error(request, 'This match is locked.')
        return redirect('room_detail', pk=room_pk)

    existing = Prediction.objects.filter(user=request.user, room=room, match=match).first()
    if existing:
        messages.info(request, f'You already predicted: {existing.predicted_winner}')
        return redirect('room_detail', pk=room_pk)

    form = PredictionForm(match, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        pred = form.save(commit=False)
        pred.user  = request.user
        pred.room  = room
        pred.match = match
        pred.save()
        messages.success(request, f'Prediction saved: {pred.predicted_winner}')
        return redirect('room_detail', pk=room_pk)

    return render(request, 'core/predict.html', {
        'form':  form,
        'room':  room,
        'match': match,
    })


@login_required
def my_predictions(request):
    predictions = Prediction.objects.filter(
        user=request.user
    ).select_related('match__league', 'room').order_by('-created_at')
    return render(request, 'core/my_predictions.html', {'predictions': predictions})


# ── Dynamic predictions ────────────────────────────────────────────────────────

@login_required
def dynamic_predict(request, ann_pk):
    ann  = get_object_or_404(Announcement, pk=ann_pk)
    room = ann.room

    if not room.is_member(request.user):
        messages.error(request, 'You are not a member of this room.')
        return redirect('rooms_list')

    if ann.is_locked or timezone.now() > ann.lock_at:
        messages.error(request, 'This challenge is locked.')
        return redirect('room_detail', pk=room.pk)

    existing = DynamicPrediction.objects.filter(announcement=ann, user=request.user).first()
    if existing:
        messages.info(request, f'You already submitted: {existing.prediction_value}')
        return redirect('room_detail', pk=room.pk)

    form = DynamicPredictionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        dp = form.save(commit=False)
        dp.announcement = ann
        dp.user         = request.user
        dp.save()
        messages.success(request, f'Submitted: {dp.prediction_value}')
        return redirect('room_detail', pk=room.pk)

    return render(request, 'core/dynamic_predict.html', {
        'form': form, 'ann': ann, 'room': room,
    })


# ── Leaderboard ────────────────────────────────────────────────────────────────

@login_required
def leaderboard(request, pk):
    room = get_object_or_404(PredictionRoom, pk=pk)

    if room.room_type == 'private' and not room.is_member(request.user):
        messages.error(request, 'Access denied.')
        return redirect('rooms_list')

    board = Points.objects.filter(room=room).select_related('user').order_by(
        '-total_points', '-streak', 'user__username'
    )

    ranked = []
    for i, row in enumerate(board, start=1):
        ranked.append({
            'rank':                i,
            'user':                row.user,
            'total_points':        row.total_points,
            'streak':              row.streak,
            'best_streak':         row.best_streak,
            'correct_predictions': row.correct_predictions,
            'total_predictions':   row.total_predictions,
            'accuracy':            row.accuracy,
        })

    user_points = Points.objects.filter(user=request.user, room=room).first()
    return render(request, 'core/leaderboard.html', {
        'room': room, 'ranked': ranked, 'user_points': user_points,
    })


# ── Match management ───────────────────────────────────────────────────────────

def _require_room_admin(request, room):
    if room.admin != request.user:
        messages.error(request, 'Only the room admin can do this.')
        return False
    return True


@login_required
def admin_dashboard(request, room_pk):
    room = get_object_or_404(PredictionRoom, pk=room_pk)
    if not _require_room_admin(request, room):
        return redirect('room_detail', pk=room_pk)

    matches = Match.objects.filter(room=room).select_related('league').prefetch_related('predictions')
    members = room.members.exclude(pk=request.user.pk)

    return render(request, 'core/admin_dashboard.html', {
        'room': room, 'matches': matches, 'members': members,
    })


@login_required
def match_add(request, room_pk):
    room = get_object_or_404(PredictionRoom, pk=room_pk)
    if not _require_room_admin(request, room):
        return redirect('room_detail', pk=room_pk)

    form = MatchForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        match        = form.save(commit=False)
        match.room   = room
        match.status = Match.Status.UPCOMING
        match.save()
        messages.success(request, f'Match added!')
        return redirect('admin_dashboard', room_pk=room.pk)

    return render(request, 'core/match_add.html', {'form': form, 'room': room})


@login_required
def match_delete(request, room_pk, match_pk):
    room  = get_object_or_404(PredictionRoom, pk=room_pk)
    match = get_object_or_404(Match, pk=match_pk, room=room)
    if not _require_room_admin(request, room):
        return redirect('room_detail', pk=room_pk)
    if request.method == 'POST':
        match.delete()
        messages.success(request, 'Match deleted.')
        return redirect('admin_dashboard', room_pk=room_pk)
    return render(request, 'core/match_delete_confirm.html', {'room': room, 'match': match})


@login_required
def match_set_live(request, room_pk, match_pk):
    room  = get_object_or_404(PredictionRoom, pk=room_pk)
    match = get_object_or_404(Match, pk=match_pk, room=room)
    if not _require_room_admin(request, room):
        return redirect('room_detail', pk=room_pk)
    if match.status == Match.Status.UPCOMING:
        match.status = Match.Status.LIVE
        match.save()
        messages.success(request, f'Match is now Live.')
    return redirect('admin_dashboard', room_pk=room_pk)


@login_required
def match_set_result(request, room_pk, match_pk):
    room  = get_object_or_404(PredictionRoom, pk=room_pk)
    match = get_object_or_404(Match, pk=match_pk, room=room)
    if not _require_room_admin(request, room):
        return redirect('room_detail', pk=room_pk)

    form = ResultForm(match, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        match.winner = form.cleaned_data['winner']
        match.status = Match.Status.FINISHED
        match.save()
        messages.success(request, 'Result saved! Scoring complete.')
        return redirect('admin_dashboard', room_pk=room_pk)

    return render(request, 'core/match_set_result.html', {
        'form': form, 'match': match, 'room': room,
    })


@login_required
def match_cancel(request, room_pk, match_pk):
    room  = get_object_or_404(PredictionRoom, pk=room_pk)
    match = get_object_or_404(Match, pk=match_pk, room=room)
    if not _require_room_admin(request, room):
        return redirect('room_detail', pk=room_pk)
    if match.status in [Match.Status.UPCOMING, Match.Status.LIVE]:
        match.status = Match.Status.CANCELLED
        match.save()
        messages.success(request, 'Match cancelled.')
    return redirect('admin_dashboard', room_pk=room_pk)


@login_required
def match_detail(request, room_pk, match_pk):
    room  = get_object_or_404(PredictionRoom, pk=room_pk)
    match = get_object_or_404(Match, pk=match_pk, room=room)

    if not room.is_member(request.user):
        messages.error(request, 'Access denied.')
        return redirect('rooms_list')

    predictions = Prediction.objects.filter(match=match, room=room).select_related('user')
    user_pred   = predictions.filter(user=request.user).first()

    return render(request, 'core/match_detail.html', {
        'room': room, 'match': match,
        'predictions': predictions, 'user_pred': user_pred,
        'is_admin': room.admin == request.user,
    })