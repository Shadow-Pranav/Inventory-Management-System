from contextvars import ContextVar

_current_organization: ContextVar = ContextVar("current_organization", default=None)


def get_current_organization():
    return _current_organization.get()


def set_current_organization(organization):
    _current_organization.set(organization)


def clear_current_organization():
    _current_organization.set(None)
