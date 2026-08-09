class InsufficientStock(Exception):
    def __init__(self, *, item, location, available, requested):
        self.item = item
        self.location = location
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient stock for {item} at {location}: "
            f"available {available}, requested {requested}"
        )
