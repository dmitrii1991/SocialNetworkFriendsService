from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from .models import User, Friendship, StatusApplicationFriends
from .enums import StatusEnum, StatusApplicationEnum


class FriendSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'email', 'username')


class UserCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'username', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            if attr == 'password':
                instance.set_password(value)
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance


class UserSerializer(serializers.ModelSerializer):
    date_joined = serializers.ReadOnlyField()
    friends = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'date_joined', 'username', 'friends')

    @swagger_serializer_method(serializer_or_field=FriendSerializer(many=True))
    def get_friends(self, obj):
        friends = User.objects.get(id=obj.id).incoming_friends.filter(status=StatusApplicationFriends.ACCEPTED)
        return FriendSerializer([i.incoming_friend for i in friends], many=True).data


class FriendshipOutSerializer(serializers.ModelSerializer):
    out_user = FriendSerializer(read_only=True, source='incoming_friend')

    class Meta:
        model = Friendship
        fields = ('id', 'out_user')


class FriendshipInSerializer(serializers.ModelSerializer):
    in_user = FriendSerializer(read_only=True, source='outgoing_friend')

    class Meta:
        model = Friendship
        fields = ('id', 'in_user')


class ResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    status = serializers.ChoiceField(StatusEnum.items())


class StatusApplicationSerializer(serializers.Serializer):
    status_application = serializers.ChoiceField(StatusApplicationEnum.items())
