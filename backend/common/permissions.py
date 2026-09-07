from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.tem_acesso_total)


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj == request.user


class IsMarketing(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.perfil == 'MARKETING' or u.tem_acesso_total))
