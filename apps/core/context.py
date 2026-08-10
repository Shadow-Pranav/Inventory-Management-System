from contextvars import ContextVar

_current_organization: ContextVar = ContextVar("current_organization", default=None)
_current_actor: ContextVar = ContextVar("current_actor", default=None)
_current_actor_scope: ContextVar = ContextVar("current_actor_scope", default="ORG")


def get_current_organization():
    return _current_organization.get()


def set_current_organization(organization):
    _current_organization.set(organization)


def clear_current_organization():
    _current_organization.set(None)


def get_current_actor():
    """The user attributed to writes made in this request — for apps/core/audit.py's signal
    receivers, which have no access to `request`."""
    return _current_actor.get()


def get_current_actor_scope():
    return _current_actor_scope.get()


def set_current_actor(user, scope="ORG"):
    _current_actor.set(user)
    _current_actor_scope.set(scope)


def clear_current_actor():
    _current_actor.set(None)
    _current_actor_scope.set("ORG")
