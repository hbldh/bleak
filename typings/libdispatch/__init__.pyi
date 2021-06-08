from typing import Optional

class dispatch_queue_attr_t: ...

DISPATCH_QUEUE_SERIAL: dispatch_queue_attr_t

class dispatch_queue_t: ...

def dispatch_queue_create(
    name: bytes, attr: Optional[dispatch_queue_attr_t]
) -> dispatch_queue_t: ...
