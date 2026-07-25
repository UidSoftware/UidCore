"""Testes do app rh (Fase E.4 -- Manutencao #7).

Cobre RF-R01 a RF-R04 e RN-R01 a RN-R03 da Especificacao_Hotfix.md.
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import Cargo, FolhaPagamento, Funcionario, RegistroFerias


def _make_user(email='admin@teste.com'):
    return User.objects.create_user(email=email, password='senha123', nome_completo='Admin Teste')


def _make_cargo(nome='Analista', salario_base=Decimal('3000.00')):
    return Cargo.objects.create(nome=nome, salario_base=salario_base)


def _make_funcionario(cargo, cpf='12345678901', nome='Funcionario Teste'):
    return Funcionario.objects.create(
        nome=nome, cpf=cpf, cargo=cargo, data_admissao='2026-01-10', salario_atual=Decimal('3000.00'),
    )


class CargoModelTest(TestCase):
    def test_criar_cargo_rf_r01(self):
        cargo = _make_cargo()
        self.assertEqual(str(cargo), 'Analista')


class FuncionarioModelTest(TestCase):
    def setUp(self):
        self.cargo = _make_cargo()

    def test_criar_funcionario_rf_r02(self):
        func = _make_funcionario(self.cargo)
        self.assertEqual(func.regime, 'CLT')

    def test_cpf_unico_rn_r01(self):
        _make_funcionario(self.cargo, cpf='11122233344', nome='A')
        with self.assertRaises(Exception):
            _make_funcionario(self.cargo, cpf='11122233344', nome='B')

    def test_soft_delete(self):
        func = _make_funcionario(self.cargo)
        func.is_active = False
        func.save()
        self.assertTrue(Funcionario.objects.filter(pk=func.pk).exists())


class FolhaPagamentoModelTest(TestCase):
    def setUp(self):
        self.cargo = _make_cargo()
        self.funcionario = _make_funcionario(self.cargo)

    def test_salario_liquido_calculado_no_save_rf_r03(self):
        folha = FolhaPagamento.objects.create(
            funcionario=self.funcionario, mes_referencia='2026-07-01',
            salario_bruto=Decimal('3000.00'), descontos=Decimal('450.00'),
        )
        self.assertEqual(folha.salario_liquido, Decimal('2550.00'))

    def test_mes_referencia_primeiro_dia_rn_r02(self):
        folha = FolhaPagamento.objects.create(
            funcionario=self.funcionario, mes_referencia=date(2026, 7, 1), salario_bruto=Decimal('3000.00'),
        )
        self.assertEqual(folha.mes_referencia.day, 1)

    def test_sem_descontos_liquido_igual_bruto(self):
        folha = FolhaPagamento.objects.create(
            funcionario=self.funcionario, mes_referencia='2026-07-01', salario_bruto=Decimal('3000.00'),
        )
        self.assertEqual(folha.salario_liquido, Decimal('3000.00'))


class RegistroFeriasModelTest(TestCase):
    def setUp(self):
        self.cargo = _make_cargo()
        self.funcionario = _make_funcionario(self.cargo)

    def test_dias_calculado_no_save_rf_r04(self):
        ferias = RegistroFerias.objects.create(
            funcionario=self.funcionario, data_inicio=date(2026, 8, 1), data_fim=date(2026, 8, 31),
        )
        self.assertEqual(ferias.dias, 30)


class FuncionarioAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.cargo = _make_cargo()

    def test_criar_funcionario_via_api_rf_r05(self):
        resp = self.client.post('/api/v1/rh/funcionarios/', {
            'nome': 'Novo Funcionario', 'cpf': '98765432100', 'cargo': self.cargo.id,
            'data_admissao': '2026-07-01', 'salario_atual': '4000.00', 'regime': 'CLT',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_destroy_faz_soft_delete_rn_r03(self):
        func = _make_funcionario(self.cargo)
        resp = self.client.delete(f'/api/v1/rh/funcionarios/{func.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        func.refresh_from_db()
        self.assertFalse(func.is_active)

    def test_listar_sem_autenticacao_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/rh/funcionarios/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class FolhaPagamentoAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)
        self.cargo = _make_cargo()
        self.funcionario = _make_funcionario(self.cargo)

    def test_criar_folha_via_api_liquido_read_only(self):
        resp = self.client.post('/api/v1/rh/folhas/', {
            'funcionario': self.funcionario.id, 'mes_referencia': '2026-07-01',
            'salario_bruto': '3000.00', 'descontos': '300.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['salario_liquido'], '2700.00')


class CargoAPITest(APITestCase):
    def setUp(self):
        self.user = _make_user()
        self.client.force_authenticate(self.user)

    def test_crud_cargos_rf_r01(self):
        resp = self.client.post('/api/v1/rh/cargos/', {
            'nome': 'Gerente', 'salario_base': '8000.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        cargo_id = resp.data['id']

        resp = self.client.delete(f'/api/v1/rh/cargos/{cargo_id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        cargo = Cargo.objects.get(pk=cargo_id)
        self.assertFalse(cargo.is_active)
