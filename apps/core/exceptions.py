class UnscopedQueryError(Exception):
    """Tenant-owned data was queried with no active organization and STRICT_TENANCY is on."""
