import typing

import android.app.appsearch
import java.lang

class DocumentIdUtil(java.lang.Object):
    @typing.overload
    @staticmethod
    def createQualifiedId(packageName: str | java.lang.String, databaseName: str | java.lang.String, document: android.app.appsearch.GenericDocument, /) -> str: ...
    @typing.overload
    @staticmethod
    def createQualifiedId(packageName: str | java.lang.String, databaseName: str | java.lang.String, namespace: str | java.lang.String, id: str | java.lang.String, /) -> str: ...
