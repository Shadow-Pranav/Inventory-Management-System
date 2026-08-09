from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from redis import Redis
from redis.exceptions import RedisError


def healthz(request):
    checks = {"db": _check_db(), "redis": _check_redis()}
    healthy = all(checks.values())
    status = "ok" if healthy else "error"
    return JsonResponse({"status": status, "checks": checks}, status=200 if healthy else 503)


def _check_db():
    try:
        connections["default"].cursor()
        return True
    except OperationalError:
        return False


def _check_redis():
    try:
        return Redis.from_url(settings.REDIS_URL).ping()
    except RedisError:
        return False
