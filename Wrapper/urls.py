from django.urls import path
from . import views

from graphene_django.views import GraphQLView

urlpatterns = [
    path('graphql', GraphQLView.as_view(graphiql=True)),
    path('', views.index, name='index'),
    path('<str:server>', views.responder, name='responder'),
    path('<str:server>/<str:nodeId>', views.responder, name='responder')
]