"""
Endpoints called BY n8n (incoming webhooks into Django).

POST /webhooks/lock-announcement/
  n8n timer fires → Django locks an announcement

Both endpoints are CSRF-exempt because n8n calls them server-to-server.
Add a secret token in production.
"""

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Announcement


@csrf_exempt
@require_POST
def lock_announcement(request):
    """
    n8n calls this when lock_at time is reached.
    Body: { "announcement_id": 5 }
    """
    try:
        body = json.loads(request.body)
        ann_id = body.get('announcement_id')
        Announcement.objects.filter(pk=ann_id, is_locked=False).update(is_locked=True)
        return JsonResponse({'status': 'locked', 'id': ann_id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)