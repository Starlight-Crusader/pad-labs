from django.urls import path
from .views import SignInView, SignUpView, IssueAccessTokenByIdView


urlpatterns = [
    path('signup', SignUpView.as_view(), name='signup'),
    path('signin', SignInView.as_view(), name='signin'),
    path('token/<int:user_id>', IssueAccessTokenByIdView.as_view(), name='token-by-id')
]