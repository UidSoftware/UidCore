# Diagrama de Atividades — UidCore

## Fluxo Principal: Login -> Dashboard -> Lancamento Financeiro -> LivroCaixa

```mermaid
flowchart TD
    START([Inicio]) --> ACESSO{Usuario tem sessao ativa?}

    ACESSO -- Sim --> DASH
    ACESSO -- Nao --> LOGIN

    subgraph Autenticacao
        LOGIN[Acessar tela de Login\n/login]
        LOGIN --> FORM_LOGIN[Preencher email e senha]
        FORM_LOGIN --> POST_TOKEN[POST /api/v1/auth/token/]
        POST_TOKEN --> TOKEN_OK{Credenciais validas?}
        TOKEN_OK -- Nao --> ERRO_LOGIN[Exibir erro de autenticacao]
        ERRO_LOGIN --> FORM_LOGIN
        TOKEN_OK -- Sim --> ZUSTAND[Salvar access_token e refresh_token\nno Zustand / localStorage]
        ZUSTAND --> FETCH_ME[GET /api/v1/accounts/me/]
        FETCH_ME --> DASH
    end

    subgraph Dashboard
        DASH[Exibir Dashboard Financeiro\n/dashboard]
        DASH --> FETCH_DASH[GET /api/v1/financeiro/dashboard/]
        FETCH_DASH --> EXIBIR[Exibir metricas:\nReceita/Despesa do mes\nSaldo Total, MRR\nProximos vencimentos\nGrafico 6 meses\nIndicadores CFO]
        EXIBIR --> NAVEGAR{Usuario navega para?}
    end

    NAVEGAR -- Financeiro --> FIN_MENU
    NAVEGAR -- Clientes --> CLI_MENU
    NAVEGAR -- Fornecedores --> FOR_MENU
    NAVEGAR -- Vendas --> VEN_MENU
    NAVEGAR -- Pagamentos --> PAG_MENU
    NAVEGAR -- RH --> RH_MENU
    NAVEGAR -- Agendamento --> AGE_MENU
    NAVEGAR -- Administrativo --> ADM_MENU
    NAVEGAR -- Portal --> PORT_MENU

    subgraph Modulo_Financeiro[Modulo: Financeiro]
        FIN_MENU[Financeiro - Escolher aba]
        FIN_MENU --> FIN_ABA{Aba selecionada?}

        FIN_ABA -- Resumo --> FIN_RESUMO[Exibir resumo do mes]
        FIN_ABA -- Contas a Receber --> LANCAMENTO_RECEITA
        FIN_ABA -- Contas a Pagar --> LANCAMENTO_DESPESA
        FIN_ABA -- Contas --> CONTA_CRUD
        FIN_ABA -- Livro Caixa --> LC_VIEW
        FIN_ABA -- DRE --> DRE_VIEW[GET /api/v1/financeiro/dre/]
        FIN_ABA -- Balanco --> BAL_VIEW[GET /api/v1/financeiro/balanco/]
        FIN_ABA -- Indicadores --> IND_VIEW[GET /api/v1/financeiro/indicadores/]
        FIN_ABA -- Conciliacao --> CONC_FLOW

        subgraph Lancamento_Receita[Lancamento de Receita]
            LANCAMENTO_RECEITA[Lista de Receitas\nGET /api/v1/financeiro/receitas/]
            LANCAMENTO_RECEITA --> NOVA_REC{Acao?}
            NOVA_REC -- Criar --> FORM_REC[Preencher formulario de receita]
            FORM_REC --> POST_REC[POST /api/v1/financeiro/receitas/]
            POST_REC --> REC_OK{Sucesso?}
            REC_OK -- Sim, status=PENDENTE --> RECEITA_CRIADA[Receita criada]
            REC_OK -- Erro --> FORM_REC
            RECEITA_CRIADA --> MARCAR_REC{Marcar como recebida?}
            MARCAR_REC -- Sim --> RECEBER[PATCH /api/v1/financeiro/receitas/{id}/receber/]
            RECEBER --> SIGNAL_REC[Signal post_save dispara]
            SIGNAL_REC --> GERA_LC_ENT[Gerar LivroCaixa ENTRADA\n+ _reconstruir_cadeia]
            NOVA_REC -- Editar --> PATCH_REC[PATCH /api/v1/financeiro/receitas/{id}/]
            NOVA_REC -- Excluir --> DELETE_REC[DELETE - is_active=False]
        end

        subgraph Lancamento_Despesa[Lancamento de Despesa]
            LANCAMENTO_DESPESA[Lista de Despesas\nGET /api/v1/financeiro/despesas/]
            LANCAMENTO_DESPESA --> NOVA_DES{Acao?}
            NOVA_DES -- Criar --> FORM_DES[Preencher formulario de despesa]
            FORM_DES --> POST_DES[POST /api/v1/financeiro/despesas/]
            POST_DES --> DES_OK{Sucesso?}
            DES_OK -- Sim, status=PENDENTE --> DESPESA_CRIADA[Despesa criada]
            DES_OK -- Erro --> FORM_DES
            DESPESA_CRIADA --> MARCAR_DES{Acao?}
            MARCAR_DES -- Pagar --> PAGAR[PATCH /api/v1/financeiro/despesas/{id}/pagar/]
            PAGAR --> SIGNAL_DES[Signal post_save dispara]
            SIGNAL_DES --> GERA_LC_SAI[Gerar LivroCaixa SAIDA\n+ _reconstruir_cadeia]
            MARCAR_DES -- Estornar --> PERFIL_EST{Usuario e ADMIN?}
            PERFIL_EST -- Nao --> BLOQUEADO[Acao negada 403]
            PERFIL_EST -- Sim --> ESTORNAR[POST /api/v1/financeiro/despesas/{id}/estornar/]
            ESTORNAR --> EST_PAR[Marcar estornado=True em AMBOS lancamentos\n+ _reconstruir_cadeia]
            NOVA_DES -- Excluir --> DELETE_DES[DELETE - is_active=False]
        end

        subgraph Conta_CRUD[Gerenciar Contas]
            CONTA_CRUD[Lista de Contas\nGET /api/v1/financeiro/contas/]
            CONTA_CRUD --> CONTA_ACT{Acao?}
            CONTA_ACT -- Criar --> POST_CONTA[POST /api/v1/financeiro/contas/]
            CONTA_ACT -- Transferir --> TRANSF[POST /api/v1/financeiro/contas/{id}/transferir/\ncom conta_destino, valor, descricao, data]
            TRANSF --> ADVISORY[pg_advisory_xact_lock(conta_origem)\npg_advisory_xact_lock(conta_destino)]
            ADVISORY --> DOIS_LC[Criar 2 lancamentos no LivroCaixa\nSAIDA na origem + ENTRADA no destino\n+ _reconstruir_cadeia em cada conta]
        end

        subgraph LC_View[Livro Caixa]
            LC_VIEW[GET /api/v1/financeiro/livro-caixa/\n+ totais]
            LC_VIEW --> LC_ESTORNO{ADMIN estornar lancamento manual?}
            LC_ESTORNO -- Sim --> POST_ESTORNO[POST /api/v1/financeiro/livro-caixa/{id}/estornar/]
            POST_ESTORNO --> EST_LC[Marcar original estornado=True\nCriar lancamento inverso estornado=True\n+ _reconstruir_cadeia]
        end

        subgraph Conciliacao_Flow[Conciliacao Bancaria]
            CONC_FLOW[Sub-aba Upload]
            CONC_FLOW --> CONC_UPLOAD[Selecionar conta, mes, PDF]
            CONC_UPLOAD --> CONC_POST[POST /api/v1/financeiro/conciliacoes/upload/\nmultipart: arquivo, conta_id, periodo, auto]
            CONC_POST --> EXTRAI[extrair_texto_pdf via pdftotext]
            EXTRAI --> PARSER{Parser disponivel para a conta?}
            PARSER -- C6/BTG --> PARSE_OK[Executar parser\nobter lista de transacoes]
            PARSER -- Sem parser --> ERRO_PARSER[Retornar 400]
            PARSE_OK --> MATCH[Matching Camada 1\ndata+valor+tipo +-1 dia]
            MATCH --> AUTO{Flag auto=True?}
            AUTO -- Sim --> MATCH2[Camada 2: assentar pendentes\nCamada 3: criar por PadraoSeguro]
            AUTO -- Nao --> SALVAR_CONC
            MATCH2 --> SALVAR_CONC[Salvar ConciliacaoExtrato + ItemConciliacao\ntransaction.atomic()]
            SALVAR_CONC --> CONC_LISTA[Sub-aba Lista\nGET /api/v1/financeiro/conciliacoes/]
            CONC_LISTA --> CONC_VER[Ver itens de uma conciliacao\nGET /conciliacoes/{id}/itens/]
            CONC_VER --> CONFIRMAR{Item FALTANDO_SISTEMA?}
            CONFIRMAR -- Sim --> POST_CONFIRMAR[POST /conciliacoes/{id}/confirmar-item/\n+ atualizar status e divergencias]
        end
    end

    subgraph Modulo_Clientes[Modulo: Clientes]
        CLI_MENU[Lista de Clientes\nGET /api/v1/clientes/]
        CLI_MENU --> CLI_ACT{Acao?}
        CLI_ACT -- Criar --> POST_CLI[POST /api/v1/clientes/\ncom soft delete em exclusao]
        CLI_ACT -- Editar --> PATCH_CLI[PATCH /api/v1/clientes/{id}/]
        CLI_ACT -- Excluir --> DELETE_CLI[is_active=False]
        CLI_ACT -- Historico --> POST_HIST[POST /api/v1/clientes/{id}/historico/]
    end

    subgraph Modulo_Fornecedores[Modulo: Fornecedores]
        FOR_MENU[Lista de Fornecedores\nGET /api/v1/fornecedores/]
    end

    subgraph Modulo_Vendas[Modulo: Vendas]
        VEN_MENU[Vendas - Orcamentos e Pedidos]
        VEN_MENU --> VEN_ABA{Sub-aba?}
        VEN_ABA -- Orcamentos --> ORC_LIST[GET /api/v1/vendas/orcamentos/\nNumeracao: ORC-YYYY-NNNN]
        VEN_ABA -- Pedidos --> PED_LIST[GET /api/v1/vendas/pedidos/\nNumeracao: PED-YYYY-NNNN]
        ORC_LIST --> ORC_STATUS[Status: RASCUNHO -> ENVIADO -> APROVADO]
        PED_LIST --> PED_STATUS[Status: PENDENTE -> CONFIRMADO -> EM_PRODUCAO -> ENTREGUE]
    end

    subgraph Modulo_Pagamentos[Modulo: Pagamentos]
        PAG_MENU[Pagamentos - Cobrancas, Parcelas, Metodos]
        PAG_MENU --> PAG_ABA{Sub-aba?}
        PAG_ABA -- Cobrancas --> COB_LIST[GET /api/v1/pagamentos/cobrancas/\nsuporte a comprovante FileField]
        PAG_ABA -- Parcelas --> PAR_LIST[GET /api/v1/pagamentos/parcelas/]
        PAG_ABA -- Metodos --> MET_LIST[GET /api/v1/pagamentos/metodos/]
    end

    subgraph Modulo_RH[Modulo: RH]
        RH_MENU[RH - Funcionarios, Folhas, Ferias, Cargos]
        RH_MENU --> RH_ABA{Sub-aba?}
        RH_ABA -- Funcionarios --> FUNC_LIST[GET /api/v1/rh/funcionarios/]
        RH_ABA -- Folhas --> FOLHA_LIST[GET /api/v1/rh/folhas/\nsalario_liquido = bruto - descontos]
        RH_ABA -- Ferias --> FER_LIST[GET /api/v1/rh/ferias/\ndias = fim - inicio]
        RH_ABA -- Cargos --> CARGO_LIST[GET /api/v1/rh/cargos/]
    end

    subgraph Modulo_Agendamento[Modulo: Agendamento]
        AGE_MENU[Agendamento - Compromissos e Agendas]
        AGE_MENU --> AGE_ABA{Sub-aba?}
        AGE_ABA -- Compromissos --> COMP_LIST[GET /api/v1/agendamento/compromissos/\nvalidacao: fim >= inicio]
        AGE_ABA -- Agendas --> AGENDA_LIST[GET /api/v1/agendamento/agendas/\ncor hex customizavel]
    end

    subgraph Modulo_Administrativo[Modulo: Administrativo]
        ADM_MENU[Administrativo - Documentos e Tipos]
        ADM_MENU --> ADM_ABA{Sub-aba?}
        ADM_ABA -- Documentos --> DOC_LIST[GET /api/v1/administrativo/documentos/\nupload de arquivo]
        ADM_ABA -- Tipos --> TIPO_LIST[GET /api/v1/administrativo/tipos/]
    end

    subgraph Modulo_Portal[Modulo: Portal do Cliente]
        PORT_MENU[Portal - Lista de Acessos\nGET /api/v1/portal/acessos/]
        PORT_MENU --> PORT_ACT{Acao?}
        PORT_ACT -- Criar acesso --> POST_PORT[POST /api/v1/portal/acessos/\nUsuario OneToOne -> Cliente]
        PORT_ACT -- Desativar --> DESATIV[PATCH /api/v1/portal/acessos/{id}/\nativo=False]
    end

    subgraph Token_Refresh[Refresh Automatico de Token]
        INTERCEPT[Interceptor Axios detecta 401]
        INTERCEPT --> REFRESH[POST /api/v1/auth/token/refresh/]
        REFRESH --> REFRESH_OK{Sucesso?}
        REFRESH_OK -- Sim --> RETRY[Retry da requisicao original]
        REFRESH_OK -- Nao --> LOGOUT[logout() - limpar Zustand\nRedirecionar para /login]
    end
```
