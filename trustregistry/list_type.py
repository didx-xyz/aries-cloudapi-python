from sqlalchemy import TypeDecorator
from sqlalchemy.sql.sqltypes import String


class StringList(TypeDecorator):
    impl = String

    def process_bind_param(self, value, _):
        if isinstance(value, list):
            return ",".join(value)

        return value

    def process_result_value(self, value, _):
        return value.split(",") if value is not None else None
