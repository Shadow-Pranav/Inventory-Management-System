from django.conf import settings


def trust_name(request):
    return {"TRUST_NAME": settings.TRUST_NAME}
