from django.http import StreamingHttpResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from redis import Redis

def _redis():
    return Redis.from_url(getattr(settings, "REDIS_URL", "redis://redis:6379/0"),
                          decode_responses=True)

@require_GET
@csrf_exempt
def battle_stream(request, battle_id: int):
    chan = f"battle:{battle_id}:events"
    r = _redis()
    pubsub = r.pubsub()
    pubsub.subscribe(chan)

    def gen():
        yield "event: ping\ndata: {}\n\n"
        try:
            for msg in pubsub.listen():
                if msg.get("type") != "message":
                    continue
                yield f"data: {msg['data']}\n\n"
        finally:
            try:
                pubsub.close()
            except Exception:
                pass

    resp = StreamingHttpResponse(gen(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp
