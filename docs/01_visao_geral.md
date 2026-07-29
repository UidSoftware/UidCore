# 01 — Visao Geral do Sistema
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Versao:** 1.0 (em producao)
**Data:** 2026-07-28
**Desenvolvido por:** Uid Software e Tecnologia LTDA

---

## 1. Proposito

O UidCore e o nucleo reutilizavel (backbone) da Uid Software para construcao de
produtos verticais SaaS destinados a MEI e pequenas empresas. Em vez de reconstruir
do zero a cada novo nicho atendido, a Uid Software mantem esse template com modulos
comuns e o adapta por segmento: pilates, salao de beleza, clinica, loja de roupa,
escola, prestador de servico, entre outros.

O sistema oferece um modulo de **CFO as a Service** embutido, fornecendo ao cliente
final controle financeiro profissional (DRE, Balanco Patrimonial, Fluxo Projetado,
Indicadores) sem precisar contratar um CFO ou contador especializado.

---

## 2. Escopo

O UidCore v1.0 cobre:

| Modulo | Descricao |
|---|---|
| Accounts | Autenticacao JWT por email, perfis de acesso, gestao de usuarios |
| Clientes | CRM basico: cadastro PF/PJ, segmentacao, historico de interacoes |
| Fornecedores | Cadastro de fornecedores PF/PJ com categorias de fornecimento |
| Financeiro | Contas, Receitas, Despesas, LivroCaixa, Aportes, Categorias, Relatorios, Conciliacao Bancaria |
| Vendas | Orcamentos, Pedidos, Itens de Pedido com numeracao automatica |
| Pagamentos | Cobrancas, Parcelas, Metodos de Pagamento |
| Administrativo | Documentos com upload, Tipos de Documento, controle de status |
| RH | Cargos, Funcionarios, Folha de Pagamento, Registro de Ferias |
| Agendamento | Agendas com cor customizavel, Compromissos vinculados a clientes |
| Portal | Acesso controlado do usuario CLIENTE ao sistema |

### Fora do escopo desta versao

- Emissao de NF-e ou NFS-e
- Modulo de estoque / inventario
- Integracao com gateway de pagamento (PIX via API, boleto bancario)
- Integracao n8n / WhatsApp
- Logica especifica de nicho (adicionada por cima do UidCore em cada produto)
- Telas proprias para o perfil CLIENTE (portal ainda sem telas implementadas)

---

## 3. Usuarios-Alvo

### Publico final (clientes dos sistemas derivados do UidCore)

- MEI e micro-empresas com faturamento ate R$ 360k/ano
- Segmentos atendidos: saude, educacao, comercio, servicos, industria, tecnologia, alimentacao
- Perfil: empreendedor sem equipe financeira dedicada, precisa de controle simples e confiavel

### Publico interno (Uid Software)

- Desenvolvedores que estendem o UidCore para novos nichos
- Agentes da esteira de IA (Forge, Loom, Sentinel) que implementam adaptacoes

---

## 4. Posicionamento — Modelo ISV/SaaS Multi-Nicho

```
UidCore (backbone)
    |
    +-- Studio Fluir (pilates)    <- ja em producao com modulo de ciclo/PSE
    +-- [Salao]                   <- proximo nicho
    +-- [Clinica]                 <- futuro
    +-- [Loja]                    <- futuro
```

Cada produto vertical herda 100% do UidCore e adiciona apenas:
- Models especificos do nicho (ex: Aula, Turma, Plano no pilates)
- Endpoints adicionais
- Telas de frontend especificas
- Regras de negocio do segmento

O UidCore nao e alterado por nicho — apenas estendido.

---

## 5. Estado Atual em Producao

**Deploy:** porta 8006, dominio uidcore.uidsoftware.com.br
**VPS:** Ubuntu 24.04, IP 209.50.241.122
**Stack:** Django 5.x + DRF + SimpleJWT + React 18 + Vite + Tailwind CSS + PostgreSQL 16

### Fases implementadas e em producao

| Fase | Conteudo | Status |
|---|---|---|
| A | common/models.py (BaseModel, PessoaBase), clientes, fornecedores | Em producao |
| B | Financeiro completo (Conta, Aporte, Categoria, Receita, Despesa, LivroCaixa, signals) | Em producao |
| C | Relatorios financeiros (DRE, Balanco, FluxoProjetado, Indicadores), endpoints | Em producao |
| D | Conciliacao bancaria (ConciliacaoExtrato, ItemConciliacao, PadraoSeguroConciliacao) | Em producao |
| E | Vendas, Pagamentos, RH, Agendamento, Administrativo, Portal | Em producao |

### Divergencias conhecidas (registradas no Levantamento)

- DIV01: App conciliacao removido — models incorporados em financeiro/models.py
- DIV02: Dashboard.jsx usa placeholders — endpoint existe mas frontend nao consome
- DIV03: Portal do cliente sem telas proprias para o perfil CLIENTE
- DIV04: is_active vs ativo — inconsistencia em AcessoPortalCliente, Agenda e PadraoSeguroConciliacao
- DIV05: MetodoPagamento tem dois campos booleanos (proprio + herdado)
- DIV06: Financeiro.jsx tem 9 abas (8 financeiro + 1 conciliacao)

---

## 6. Beneficios Esperados

| Beneficio | Para quem |
|---|---|
| Reducao de tempo de desenvolvimento por nicho | Uid Software (dev) |
| Modulo financeiro profissional sem custo adicional | Cliente final |
| DRE, Balanco e Fluxo Projetado automaticos | Cliente final (MEI/micro-empresa) |
| Conciliacao bancaria semi-automatica | Cliente final |
| Portal do cliente para acesso proprio | Cliente final (usuario CLIENTE) |
| Base testada e reutilizavel para expansao | Uid Software (negocio) |

---

## 7. Referencias

- ArquiteturaTecnica#2 (SystemD — banco do SystemD)
- Manutencao#7 (UidCore — historico de execucoes no CLAUDE.md do projeto)
- Studio Fluir: primeiro produto derivado do UidCore (em producao desde mai/2026)
