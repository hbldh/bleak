from collections.abc import Callable

import java.chaquopy
import java.lang

class App:
    def request_permissions(
        self,
        permissions: list[str],
        on_complete: Callable[
            [java.chaquopy.JavaArray[java.lang.String], java.chaquopy.JavaArrayJInt],
            None,
        ],
    ) -> None: ...
