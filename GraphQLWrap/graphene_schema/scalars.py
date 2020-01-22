from graphene.types import Scalar
from graphql.language import ast

import datetime


class OPCUADataVariable(Scalar):
    """
    Custom scalar type that accepts all common data types.

    Formats datetime objects into JSONifiable format.
    Supports multiple different value types
    (int, float, datetime, string(without '.'), boolean).
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
        if isinstance(node, ast.StringValue):
            value = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
        elif "." in value:
            value = float(value)
        elif value.isdigit():
            value = int(value)
        elif value in ("True", "true"):
            value = True
        elif value in ("False", "false"):
            value = False
        return value

    @staticmethod
    def parse_value(value):
        if isinstance(value, (datetime.date, datetime.datetime)):
            value = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
        elif "." in value:
            value = float(value)
        elif value.isdigit():
            value = int(value)
        elif value in ("True", "true"):
            value = True
        elif value in ("False", "false"):
            value = False
        return value
