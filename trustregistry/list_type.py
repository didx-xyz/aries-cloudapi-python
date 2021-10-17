from sqlalchemy import TypeDecorator
from sqlalchemy.sql.sqltypes import String


class StringList(TypeDecorator):
    impl = String

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def process_bind_param(self, value, dialect):
        if isinstance(value, list):
            return ",".join(value)

        return value

    def process_result_value(self, value, dialect):
        return value.split(",") if value is not None else None
