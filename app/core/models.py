from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

from .managers import UserManager


class StatusApplicationFriends(models.TextChoices):
    ACCEPTED = 'ACC', gettext_lazy('Заявка принята')
    REJECTED = 'REJ', gettext_lazy('Заявка отклонена')
    SUBMITTED = 'SUB', gettext_lazy('Заявка подана')


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=40, unique=True, blank=False, verbose_name='Никнейм')
    email = models.EmailField(max_length=40, unique=True, verbose_name='Почта')
    first_name = models.CharField(max_length=30, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=30, blank=True, verbose_name='Фамилия')
    is_active = models.BooleanField(default=True, verbose_name='Активный')
    is_staff = models.BooleanField(default=False, verbose_name='Aдминистратор')
    is_superuser = models.BooleanField(default=False, verbose_name='++')
    date_joined = models.DateTimeField(default=timezone.now, verbose_name='Время Регистрации')
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self) -> str:
        return f'{self.username}/{self.email}'


class Friendship(models.Model):
    outgoing_friend = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='От кого',
        related_name='outgoing_friends',
        null=False
    )
    incoming_friend = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Кому',
        related_name='incoming_friends',
        null=False
    )
    status = models.CharField(
        max_length=3,
        choices=StatusApplicationFriends.choices,
    )
    friendship_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Завка в друзья'
        verbose_name_plural = 'Заявки в друзья'
        unique_together = ('outgoing_friend', 'incoming_friend')

    def __str__(self) -> str:
        return f'{self.outgoing_friend} => {self.incoming_friend}  status={self.status}'
