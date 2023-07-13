from django.urls import path
from .views import (
    ApplicationAPIView,
    CreateUserAPIView,
    FriendsViewSet,
    SubmittedApplicationOutViewSet,
    SubmittedApplicationInViewSet,
    UserAPIView,
    UserMeAPIView,
)

urlpatterns = [
    path('create/', CreateUserAPIView.as_view(), name='user_create'),
    path('<pk>/', UserAPIView.as_view(), name='user'),
    path('<pk>/application/', ApplicationAPIView.as_view(), name='user_application'),
    path('me/profile/', UserMeAPIView.as_view(), name='user_me_profile'),
    path('me/friends/', FriendsViewSet.as_view(), name='user_me_friends'),
    path('me/submitted/out/', SubmittedApplicationOutViewSet.as_view(), name='user_me_submitted_out'),
    path('me/submitted/in/', SubmittedApplicationInViewSet.as_view(), name='user_me_submitted_in'),
]
