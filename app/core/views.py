from django.shortcuts import get_object_or_404
from django.db.utils import IntegrityError
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import (
    FriendSerializer,
    FriendshipOutSerializer,
    FriendshipInSerializer,
    UserSerializer,
    UserCreateSerializer,
    ResponseSerializer,
    StatusApplicationSerializer,
)
from .models import Friendship, User, StatusApplicationFriends
from .enums import StatusEnum, StatusApplicationEnum


class CreateUserAPIView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        operation_description="Создание пользователя",
        responses={
            201: 'Пользователь успешно создан',
            400: 'Пользователь c email/username существует',
            'Shema': UserCreateSerializer
        }
    )
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserMeAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_description="Возвращает детальную информацию о собственном профиле",
        responses={
            200: 'Успех',
            'Shema': UserSerializer
        }
    )
    def get(self, request):
        JWT_authenticator = JWTAuthentication()
        response = JWT_authenticator.authenticate(request)
        if response is not None:
            user, token = response
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)


class UserAPIView(generics.RetrieveAPIView, generics.DestroyAPIView):
    """
    get:
    Возвращает детальную информацию о выбранном профиле

    """
    queryset = User.objects.select_related()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer(self, *args, **kwargs):
        return UserSerializer(*args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if (friendship := Friendship.objects.filter(
            outgoing_friend=self.request.user,
            incoming_friend=self.get_object(),
            status=StatusApplicationFriends.ACCEPTED
        )).exists():
            friendship.update(status=StatusApplicationFriends.REJECTED)
            Friendship.objects.filter(
                outgoing_friend=self.get_object(),
                incoming_friend=self.request.user,
                status=StatusApplicationFriends.ACCEPTED
            ).update(status=StatusApplicationFriends.REJECTED)
            return Response(status=status.HTTP_200_OK)
        return Response({"detail": "Вы не можете удалить из друзей"}, status=status.HTTP_400_BAD_REQUEST)


class FriendsViewSet(generics.ListAPIView):
    serializer_class = FriendSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return [i.incoming_friend for i in User.objects.get(
            id=self.request.user.id
        ).incoming_friends.filter(
            status=StatusApplicationFriends.ACCEPTED
        )]


class SubmittedApplicationOutViewSet(generics.ListAPIView):
    """
    get:
    Возвращает список исходящих заявок
    """
    serializer_class = FriendshipOutSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Friendship.objects.filter(outgoing_friend=self.request.user, status=StatusApplicationFriends.SUBMITTED)


class SubmittedApplicationInViewSet(generics.ListAPIView):
    """
    get:
    Возвращает список входящих заявок
    """
    serializer_class = FriendshipInSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Friendship.objects.filter(incoming_friend=self.request.user, status=StatusApplicationFriends.SUBMITTED)


class ApplicationAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_description="Отправка/одобрение заявки",
        responses={
            200: 'Успешная отправка/добавление',
            400: 'Ошибка',
            'Shema': ResponseSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        JWT_authenticator = JWTAuthentication()
        user, token = JWT_authenticator.authenticate(request)
        friend = get_object_or_404(User, id=self.kwargs['pk'])
        friendship_reverse = Friendship.objects.filter(outgoing_friend=friend, incoming_friend=user)
        if user == friend:
            return Response({"detail": "Вы не можете отправить заявку самому себе"}, status=status.HTTP_400_BAD_REQUEST)
        response = {"status": StatusEnum.SUCCESS}
        if friendship_reverse.exists() and friendship_reverse[0].status == StatusApplicationFriends.SUBMITTED:
            friendship_reverse.update(status=StatusApplicationFriends.ACCEPTED)
            Friendship(outgoing_friend=user, incoming_friend=friend, status=StatusApplicationFriends.ACCEPTED).save()
            response.update({"detail": "Вы теперь друзья"})
        elif friendship_reverse.exists() and friendship_reverse[0].status == StatusApplicationFriends.ACCEPTED:
            return Response({"detail": "Вы и так друзья"}, status=status.HTTP_400_BAD_REQUEST)
        elif friendship_reverse.exists() and friendship_reverse[0].status == StatusApplicationFriends.REJECTED:
            return Response(
                {"status": StatusEnum.UNSUCCESS, "detail": "Вы не сможете стать друзьями"},
                status=status.HTTP_200_OK
            )
        elif not friendship_reverse.exists():
            try:
                Friendship(
                    outgoing_friend=user, incoming_friend=friend, status=StatusApplicationFriends.SUBMITTED
                ).save()
                response |= {"detail": "Заявка успешно отправлена"}
            except IntegrityError:
                return Response({"detail": "Заявка и так отправлена"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            response |= {"detail": "Заявка успешно отправлена"}
        return Response(response, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="Отмена иходящей/ удадение входящей заявки",
        responses={
            200: 'Успешное удаление/омена',
            400: 'Ошибка',
            'Shema': ResponseSerializer
        }
    )
    def delete(self, request, *args, **kwargs):
        JWT_authenticator = JWTAuthentication()
        user, token = JWT_authenticator.authenticate(request)
        friend = get_object_or_404(User, id=self.kwargs['pk'])
        if user == friend:
            return Response({"detail": "Вы не можете удалить самого себя!"}, status=status.HTTP_400_BAD_REQUEST)
        friendship_reverse = Friendship.objects.filter(outgoing_friend=friend, incoming_friend=user)
        response = {"status": StatusEnum.SUCCESS}
        if friendship_reverse.exists() and friendship_reverse[0].status == StatusApplicationFriends.SUBMITTED:
            friendship_reverse.update(status=StatusApplicationFriends.REJECTED)
            Friendship(outgoing_friend=user, incoming_friend=friend, status=StatusApplicationFriends.REJECTED).save()
            response |= {"detail": "Заявка отклонена. Следующие будут автоматом отклонены"}
        elif friendship_reverse.exists() and friendship_reverse[0].status == StatusApplicationFriends.REJECTED:
            return Response(
                {"status": StatusEnum.UNSUCCESS, "detail": "Заявкf была уже отклонена"}, status=status.HTTP_200_OK
            )
        elif (friendship := Friendship.objects.filter(
                outgoing_friend=user,
                incoming_friend=friend,
                status=StatusApplicationFriends.SUBMITTED
            )
        ).exists():
            friendship.delete()
            response |= {"detail": "Заявка отменена"}
        else:
            return Response({"detail": "Заявки не существует"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(response, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Получение статуса заявки",
        responses={
            200: 'Успешное удаление/омена',
            400: 'Ошибка',
            'Shema': StatusApplicationSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        JWT_authenticator = JWTAuthentication()
        user, token = JWT_authenticator.authenticate(request)
        friend = get_object_or_404(User, id=self.kwargs['pk'])
        if user == friend:
            return Response({"detail": "Не можете выбрать себя"}, status=status.HTTP_400_BAD_REQUEST)
        friendship_reverse = Friendship.objects.filter(outgoing_friend=friend, incoming_friend=user)
        if friendship_reverse.exists() and friendship_reverse[0].status == StatusApplicationFriends.SUBMITTED:
            return Response({"status": StatusApplicationEnum.OUT}, status=status.HTTP_200_OK)
        elif friendship_reverse.exists() and friendship_reverse[0].status == StatusApplicationFriends.ACCEPTED:
            return Response({"status": StatusApplicationEnum.FRI}, status=status.HTTP_200_OK)
        elif friendship_reverse.exists() and friendship_reverse[0].status == StatusApplicationFriends.REJECTED:
            return Response({"status": StatusApplicationEnum.REJ}, status=status.HTTP_200_OK)
        elif Friendship.objects.filter(
            outgoing_friend=user, incoming_friend=friend, status=StatusApplicationFriends.SUBMITTED
        ).exists():
            return Response({"status": StatusApplicationEnum.IN}, status=status.HTTP_200_OK)
        else:
            return Response({"status": StatusApplicationEnum.NONE}, status=status.HTTP_200_OK)
