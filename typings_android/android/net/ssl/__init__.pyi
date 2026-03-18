import java
import java.chaquopy
import java.lang
import javax.net.ssl

class SSLEngines(java.lang.Object):
    @staticmethod
    def exportKeyingMaterial(engine: javax.net.ssl.SSLEngine, label: str | java.lang.String, context: java.chaquopy.JavaArrayJByte, length: int | java.jint | java.lang.Integer, /) -> java.chaquopy.JavaArrayJByte | None: ...
    @staticmethod
    def isSupportedEngine(engine: javax.net.ssl.SSLEngine, /) -> bool: ...
    @staticmethod
    def setUseSessionTickets(engine: javax.net.ssl.SSLEngine, useSessionTickets: bool | java.jboolean | java.lang.Boolean, /) -> None: ...

class SSLSockets(java.lang.Object):
    @staticmethod
    def exportKeyingMaterial(socket: javax.net.ssl.SSLSocket, label: str | java.lang.String, context: java.chaquopy.JavaArrayJByte, length: int | java.jint | java.lang.Integer, /) -> java.chaquopy.JavaArrayJByte | None: ...
    @staticmethod
    def isSupportedSocket(socket: javax.net.ssl.SSLSocket, /) -> bool: ...
    @staticmethod
    def setUseSessionTickets(socket: javax.net.ssl.SSLSocket, useSessionTickets: bool | java.jboolean | java.lang.Boolean, /) -> None: ...
