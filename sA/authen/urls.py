from django.urls import path
from .views import SignInView, SignUpView, IssueAccessTokenView


urlpatterns = [
    path('signup', SignUpView.as_view(), name='signup'),
    path('signin', SignInView.as_view(), name='signin'),
    path('token', IssueAccessTokenView.as_view(), name='token')
]