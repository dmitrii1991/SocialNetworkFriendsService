from django.contrib import admin

from .models import User, Friendship


class UserAdmin(admin.ModelAdmin):
    list_display = ['username']
    search_fields = ('username',)
    fieldsets = (
        ('Данные пользователя', {'fields': ('username', 'email')}),
        ('Статус', {'fields': ('is_active', )}),
        ('Данные учетки', {'fields': ('last_login', 'date_joined')}),
    )


class FriendshipAdmin(admin.ModelAdmin):
    list_display = (
        'outgoing_friend',
        'incoming_friend',
        'status',
        'friendship_date'
    )
    search_fields = (
        'outgoing_friend',
        'incoming_friend',
        'status'
    )
    save_on_top = True


admin.site.register(User, UserAdmin)
admin.site.register(Friendship, FriendshipAdmin)
