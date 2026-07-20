import re
from django.core.exceptions import ValidationError


def validar_cpf(value):
    cpf = re.sub(r'\D', '', str(value))
    if len(cpf) != 11:
        raise ValidationError('CPF deve conter 11 dígitos.')
    if cpf == cpf[0] * 11:
        raise ValidationError('CPF inválido.')
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[9]):
        raise ValidationError('CPF inválido.')
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf[10]):
        raise ValidationError('CPF inválido.')


def validar_cnpj(value):
    cnpj = re.sub(r'\D', '', str(value))
    if len(cnpj) != 14:
        raise ValidationError('CNPJ deve conter 14 dígitos.')
    if cnpj == cnpj[0] * 14:
        raise ValidationError('CNPJ inválido.')
    pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos[i] for i in range(12))
    resto = soma % 11
    dig1 = 0 if resto < 2 else 11 - resto
    if int(cnpj[12]) != dig1:
        raise ValidationError('CNPJ inválido.')
    pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos[i] for i in range(13))
    resto = soma % 11
    dig2 = 0 if resto < 2 else 11 - resto
    if int(cnpj[13]) != dig2:
        raise ValidationError('CNPJ inválido.')


def validar_documento(value):
    digitos = re.sub(r'\D', '', str(value))
    if len(digitos) == 11:
        validar_cpf(digitos)
    elif len(digitos) == 14:
        validar_cnpj(digitos)
    else:
        raise ValidationError('Documento deve ser CPF (11 dígitos) ou CNPJ (14 dígitos).')
