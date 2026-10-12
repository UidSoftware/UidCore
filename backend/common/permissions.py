from rest_framework.permissions import BasePermission, SAFE_METHODS


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


class IsFinanceiro(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.perfil == 'FINANCEIRO' or u.tem_acesso_total))


class IsProfissional(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.perfil == 'PROFISSIONAL' or u.tem_acesso_total))


class BloqueiaEscritaDeProfissional(BasePermission):
    """
    RF-06 (Manutencao 63) — Cliente em leitura para PROFISSIONAL. Nao e o
    mesmo padrao de IsFinanceiro/IsProfissional (grant-style) porque aqui a
    regra e "nega escrita SO para esse perfil, mantem os demais exatamente
    como estao" -- nao daria pra compor so com | / ~ sobre um grant-style
    sem tambem bloquear quem tem tem_acesso_total (ADMIN/SUPERADMIN), que
    IsProfissional.has_permission tambem retorna True para eles. Consulta
    IsProfissional() diretamente (nao decorativo -- e o "alguem le
    IsProfissional" exigido pelo item 5 do pedido, com teste proprio).
    """
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        eh_profissional_puro = (
            IsProfissional().has_permission(request, view)
            and not u.tem_acesso_total
            and u.perfil == 'PROFISSIONAL'
        )
        return not eh_profissional_puro
