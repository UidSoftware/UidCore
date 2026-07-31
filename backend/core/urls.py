from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/clientes/', include('clientes.urls')),
    path('api/v1/fornecedores/', include('fornecedores.urls')),
    path('api/v1/produtos/', include('produtos.urls')),
    path('api/v1/vendas/', include('vendas.urls')),
    path('api/v1/pagamentos/', include('pagamentos.urls')),
    path('api/v1/administrativo/', include('administrativo.urls')),
    path('api/v1/rh/', include('rh.urls')),
    path('api/v1/agendamento/', include('agendamento.urls')),
    path('api/v1/portal/', include('portal.urls')),
    path('api/v1/financeiro/', include('financeiro.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
