from django.contrib import admin
from .models import User, UserProfile, Privilege, UserPrivilege

class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'phone_number', 'first_name', 'last_name', 'is_active', 'is_admin')
    search_fields = ('email', 'phone_number')
    list_filter = ('is_active', 'is_admin')

admin.site.register(User, UserAdmin)

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio', 'date_of_birth', 'avatar')
    search_fields = ('user__email',)

admin.site.register(UserProfile, UserProfileAdmin)


class PrivilegeAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)

admin.site.register(Privilege, PrivilegeAdmin)

class UserPrivilegeAdmin(admin.ModelAdmin):
    list_display = ('user', 'privilege', 'purchased_at')
    search_fields = ('user__email', 'privilege__name')
    list_filter = ('purchased_at',)

admin.site.register(UserPrivilege, UserPrivilegeAdmin)
