from django.urls import path
from .views import SignInView, SignUpView, ValidateTokenForBView


urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('signin/', SignInView.as_view(), name='signin'),
    path('validate-token/', ValidateTokenForBView.as_view(),  name='validate-token'),
]