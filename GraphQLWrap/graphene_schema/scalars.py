from graphene.types import Scalar
from graphql.language.ast import StringValue, IntValue, FloatValue, \
    BooleanValue, EnumValue

import datetime


class OPCUADataVariable(Scalar):
    """
    Custom scalar type that accepts all common data types.

    Formats datetime objects into JSONifiable format.
    Supports multiple different value types
    (int, float, datetime, string, boolean).
    """

    class Meta():
        description = __doc__

    # Serialization for returned values
    @staticmethod
    def serialize(value):
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()
        return value

    # Parsing for inputted value
    @staticmethod
    def parse_literal(node):
        value = node.value
        if isinstance(node, IntValue):
            num = int(value)
            if -2147483648 <= num <= 2147483647:
                return num
        elif isinstance(node, FloatValue):
            return float(value)
        elif isinstance(node, BooleanValue):
            return value
        elif isinstance(node, StringValue):
            try:
                dt = datetime.datetime.strptime(
                    value,
                    "%Y-%m-%dT%H:%M:%S.%f"
                )
                return dt
            except ValueError:
                return str(value)
        elif isinstance(node, EnumValue):
            if (value == "True") or (value == "true"):
                return True
            elif (value == "False") or (value == "false"):
                return False
            return str(value)

    @staticmethod
    def parse_value(value):
        return value
