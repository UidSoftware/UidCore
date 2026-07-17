# UidCore — Template Financeiro Multi-Nicho

> Sistema-template (núcleo/backbone) para os produtos verticais da Uid Software — modelo ISV/SaaS por nicho (pilates, salão, loja, clínica etc.), com módulo financeiro "CFO as a Service" para MEI e pequenas empresas.

---

## Visão Geral

Sistema-template (núcleo/backbone) para ser a base de todos os futuros produtos verticais da Uid Software (modelo ISV/SaaS por nicho: pilates, salão, loja de roupa, clínica etc. — já validado com o Studio Fluir em produção). A ideia partiu do próprio fundador (Luiz) ao perceber que módulos como cadastro de clientes, fornecedores, financeiro, vendas, pagamentos, administrativo, funcionários/RH, agendamento e área do usuário se repetem em praticamente todo nicho atendido. Construir esse núcleo uma vez, bem feito, e adaptar por segmento — em vez de reconstruir do zero a cada novo cliente.

## Módulos Comuns

- Cadastro de Clientes (CRM básico: dados, histórico, segmentação)
- Cadastro de Fornecedores (dados, CNPJ, contato, categorias de fornecimento)
- Vendas (pedidos, orçamentos, propostas, funil comercial simplificado)
- Pagamentos (recebimento de clientes, integração com meios de pagamento — PIX, boleto, cartão)
- Administrativo (documentos, contratos, processos internos)
- Funcionários / RH (cadastro, folha de pagamento básica, férias, admissão/demissão)
- Agendamento (controle de compromissos/horários — módulo genérico reaproveitável por clínica, salão, estúdio, prestador de serviço em geral)
- Área do Usuário / Portal do Cliente — acesso próprio pro cliente final (perfil separado de admin/operacional) ver seus próprios dados: faturas, agendamentos, histórico, chamados/suporte — sem precisar entrar em contato pra tudo. Segue o mesmo padrão que já existe no SystemD (perfil CLIENTE: MeusProjetos, Suporte, MinhasFaturas).
- Financeiro (módulo mais crítico e diferenciado — ver seção dedicada abaixo)

## Módulo Financeiro — "CFO as a Service" para MEI/Pequenas/Médias Empresas

A maior dor do público-alvo não é só ter uma planilha organizada — é não ter um CFO/controller que traduza os números em decisão. O módulo financeiro do template deve ir além do livro-caixa básico e entregar, de forma automatizada, o que um CFO faria manualmente:

1. Contas a Pagar / Contas a Receber com status (Pendente/Pago-Recebido/Atrasado/Cancelado), vencimento, categorização automática por fornecedor/cliente recorrente, e alertas de vencimento próximo.
2. Livro Caixa imutável (fonte da verdade, regime de caixa), com saldo por conta, nunca editável diretamente — correções sempre via estorno (auditoria completa).
3. DRE automatizado (mensal/anual), regime de competência, por categoria de receita/despesa, sem depender de fechamento manual de contador.
4. Balanço Patrimonial automatizado — Ativo (caixa/bancos, contas a receber, imobilizado), Passivo (contas a pagar, empréstimos) e Patrimônio Líquido (capital social + lucros/prejuízos acumulados), mantendo a equação contábil Ativo = Passivo + Patrimônio Líquido sempre batendo.
5. EBITDA — calculado a partir do DRE, como indicador de geração operacional de caixa antes de juros, impostos, depreciação e amortização.
6. Vinculação DRE ↔ Balanço Patrimonial — o resultado do período (lucro ou prejuízo) apurado no DRE deve refletir automaticamente no Patrimônio Líquido do Balanço (conta de Lucros/Prejuízos Acumulados), garantindo consistência contábil real entre os dois demonstrativos — não dois relatórios desconectados, e sim peças de uma mesma contabilidade íntegra.
7. Fluxo de Caixa projetado — não só o passado, mas a projeção dos próximos 30/60/90 dias considerando contas a pagar/receber já cadastradas (o que vai faltar ou vai sobrar antes que aconteça).
8. Indicadores de CFO: margem líquida, ponto de equilíbrio, ticket médio, MRR/receita recorrente (quando aplicável), runway de caixa, comparativo mês a mês/ano a ano.
9. Categorização inteligente de despesas — inferência automática de categoria a partir da descrição (já existe um protótipo funcional em financeiro/parsers.py::inferir_categoria_descricao no SystemD; migrar/generalizar para o template).
10. Dashboard executivo com KPIs visuais (semelhante ao dashboard/ já existente no SystemD: receita_mes, despesa_mes, resultado_mes, receitas/despesas a vencer e atrasadas).
11. Multi-conta (corrente, poupança, caixa, carteira digital) com transferência entre contas e saldo consolidado.
12. Transparência total: LivroCaixa nunca é editado, só estornado — dá pro dono do MEI confiar no número sem confiar cegamente no sistema.

## Conciliação Bancária Automática

Um dos maiores gargalos do MEI/pequena empresa é bater o extrato do banco com o que está lançado no sistema — hoje isso é manual, mensal, sujeito a erro humano, e geralmente só o contador faz (com atraso). Construímos hoje no SystemD um pipeline funcional que deve ser generalizado como módulo padrão do template:

a) Leitura automática do extrato direto da nuvem: mount via rclone do provedor de armazenamento (Dropbox no caso do SystemD, mas o padrão serve para Google Drive/OneDrive) — não depende de nenhum notebook/dispositivo ligado; os PDFs chegam na nuvem (ex: cliente exporta do app do banco e salva na pasta sincronizada) e o servidor lê direto de lá.
b) Watchdog (systemd service) monitorando a pasta a cada poucos minutos, disparando o parsing assim que um extrato novo aparece.
c) Parsing de PDF (mesmo com senha) via pikepdf + pdftotext, com parser dedicado por banco (parse_c6, parse_btg no SystemD — no template, generalizar para os bancos mais usados por MEI: Nubank, Inter, C6, BTG, Caixa, Itaú).
d) Matching em 3 camadas, da mais segura para a menos segura:
   1. Bate contra o LivroCaixa (já lançado) — concilia direto.
   2. Bate contra Despesa/Receita PENDENTE/ATRASADA (conta a pagar/receber já cadastrada, ainda não paga) — assenta automaticamente (marca como paga/recebida), nunca duplica.
   3. Só cria lançamento novo do zero para padrões conhecidos e seguros (ex: rendimento de conta remunerada) — qualquer coisa fora disso fica pendente para revisão humana, nunca é criado às cegas.
e) Regra inegociável: dinheiro real está envolvido — o sistema nunca deve criar lançamento novo sem correspondência clara (pendente batendo ou padrão aprovado). Ambiguidade sempre vira revisão humana, nunca decisão automática.
f) Já existe uma Manutenção (#3) na fila do pipeline do SystemD pedindo a tela de revisão de pendências + gestão de padrões seguros — usar como referência de UX para replicar no template.

## Arquitetura / Replicabilidade

Esse sistema deve nascer desenhado para ser o esqueleto reaproveitado a cada novo nicho (como já acontece hoje manualmente entre Studio Fluir e SystemD) — módulos de clientes/fornecedores/financeiro/vendas/RH/agendamento/área do usuário como camada comum, com espaço claro para customização por segmento (ex: agenda de aulas pro Studio Fluir, prontuário pra clínica, etc). Avaliar na fase de Arquitetura Técnica se o melhor caminho é monorepo de apps Django reaproveitáveis (apps plugáveis) ou fork por cliente com merge seletivo de atualizações do núcleo.

## Público-Alvo

MEI, pequenas e médias empresas de qualquer segmento que precisem de um ERP enxuto com módulo financeiro forte — do microempreendedor que hoje usa caderno/planilha até a pequena empresa que já paga por um sistema genérico caro e não usa nem metade dele.

## Concorrentes de Referência

Conta Azul, Omie, Bling, Tiny ERP, Nibo, Granatum — nenhum deles entrega o nível de automação de conciliação bancária + matching contra contas a pagar/receber pendentes que construímos hoje, nem a vinculação real entre DRE e Balanço Patrimonial nesse nível de simplicidade para o público MEI; esse é um diferencial real.

---

## Palavras-Chave

ERP MEI, CFO as a service, conciliação bancária automática, fluxo de caixa projetado, DRE, balanço patrimonial, EBITDA, agendamento, área do usuário, sistema multi-nicho, template SaaS vertical

---

## Stack Técnica (Arquitetura Técnica #2)

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python + Django REST Framework |
| Banco | PostgreSQL |
| Autenticação | JWT |
| Padrão API | REST |
| Frontend | React 18 + Vite |
| Estilização | Tailwind CSS |
| Estado global | Zustand |
| Server state | TanStack Query |
| Deploy | VPS própria (Uid Software) + Nginx |
| Integrações | n8n, WhatsApp API |

---

## Projeto

- **Responsável:** Luiz Eduardo
- **Cliente/Prospecto:** Uid Software e Tecnologia LTDA
- **Origem:** Entrevista + Arquitetura Técnica registradas no SystemD
- **Pipeline:** Planner → Analista → doc-generator → Blueprint + Brush → Forge + Loom → Sentinel → Pilot (Claw Empire)

---

*Uid Software e Tecnologia LTDA — Uberlândia/MG*
