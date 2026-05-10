from django.urls import path
from . import views
from .webhooks import lock_announcement

urlpatterns = [
    # Auth
    path('',          views.home,          name='home'),
    path('register/', views.register_view, name='register'),
    path('login/',    views.login_view,    name='login'),
    path('logout/',   views.logout_view,   name='logout'),

    # Rooms
    path('rooms/',                 views.rooms_list,  name='rooms_list'),
    path('rooms/create/',          views.room_create, name='room_create'),
    path('rooms/<int:pk>/',        views.room_detail, name='room_detail'),
    path('rooms/join/',            views.room_join,   name='room_join'),
    path('rooms/<int:pk>/delete/', views.room_delete, name='room_delete'),

    # Transfer admin
    path('rooms/<int:room_pk>/transfer-admin/<int:user_pk>/',
         views.transfer_admin, name='transfer_admin'),

    # Chat
    path('rooms/<int:room_pk>/chat/messages/', views.chat_messages_json, name='chat_messages_json'),
    path('rooms/<int:room_pk>/chat/send/',     views.chat_send,          name='chat_send'),

    # Predictions
    path('rooms/<int:room_pk>/predict/<int:match_pk>/', views.predict,        name='predict'),
    path('my-predictions/',                             views.my_predictions, name='my_predictions'),

    # Leaderboard
    path('rooms/<int:pk>/leaderboard/', views.leaderboard, name='leaderboard'),

    # Announcements
    path('rooms/<int:room_pk>/announcements/',
         views.announcement_list, name='announcement_list'),
    path('rooms/<int:room_pk>/announcements/create/',
         views.announcement_create, name='announcement_create'),
    path('rooms/<int:room_pk>/announcements/<int:ann_pk>/lock/',
         views.announcement_lock, name='announcement_lock'),
    path('rooms/<int:room_pk>/announcements/<int:ann_pk>/outcome/',
         views.announcement_set_outcome, name='announcement_set_outcome'),
    path('announcements/<int:ann_pk>/predict/',
         views.dynamic_predict, name='dynamic_predict'),

    # n8n webhook
    path('webhooks/lock-announcement/', lock_announcement, name='lock_announcement'),

    # Match management
    path('rooms/<int:room_pk>/dashboard/',
         views.admin_dashboard, name='admin_dashboard'),
    path('rooms/<int:room_pk>/matches/add/',
         views.match_add, name='match_add'),
    path('rooms/<int:room_pk>/matches/<int:match_pk>/',
         views.match_detail, name='match_detail'),
    path('rooms/<int:room_pk>/matches/<int:match_pk>/live/',
         views.match_set_live, name='match_set_live'),
    path('rooms/<int:room_pk>/matches/<int:match_pk>/result/',
         views.match_set_result, name='match_set_result'),
    path('rooms/<int:room_pk>/matches/<int:match_pk>/cancel/',
         views.match_cancel, name='match_cancel'),
    path('rooms/<int:room_pk>/matches/<int:match_pk>/delete/',
         views.match_delete, name='match_delete'),
]