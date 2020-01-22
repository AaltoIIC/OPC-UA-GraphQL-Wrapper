from graphene import Schema
from graphene_schema.query import Query
from graphene_schema.mutation import Mutation
# from graphene_schema.subscription import Subscription

schema = Schema(
    query=Query,
    mutation=Mutation,
    # subscription=Subscription,
)
