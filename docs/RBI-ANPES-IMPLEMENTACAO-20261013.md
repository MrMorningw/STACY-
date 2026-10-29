# RBI — ANPES: Auto Núcleo Pessoal Eficiente STACY

> **Nota de estado (2026-10-28):** este documento é um registro histórico da etapa de 2026-10-13. A arquitetura ativa do APK foi posteriormente migrada para Kotlin/Android nativo e não depende operacionalmente de Termux/Python. Para o estado atual da autoconsulta e atualização, consulte `docs/ARS-AUTOATUALIZACAO-SEGURA.md` e `docs/RBI-INTEGRIDADE-IDENTIDADE-ATUALIZACOES-20261013.md`.



**Data:** 13/10/2026  
**Branch de trabalho:** `stacy-anpes-core-20261013`  
**Integração atual:** política de autonomia conectada ao `StacyOrchestrator` por meio do contrato compatível `autonomy.py`; consulta determinística de estado do ANPES adicionada.
**Base:** commit `9c6bafe4cdd92c0a3e1639a40ac83e7b3caf18bd` da branch de integração Android ↔ CORE.  
**Objetivo:** evoluir a STACY para uma assistente pessoal capaz de planejar, executar, testar e verificar tarefas autorizadas, preservando o CORE, os MPEFs e a identidade visual existentes.

## 1. Decisão arquitetural

ANPES será uma camada de autonomia controlada sobre o CORE existente, não um segundo orquestrador independente. O fluxo-alvo é:

`Interface/voz → ponte Android → CORE → ANPES (plano e política) → executor registrado → verificação do resultado → resposta/relatório RBI`

A IA pode sugerir um plano, mas não pode autorizar a si mesma nem transformar texto em comando arbitrário. O CORE valida o plano; executores tipados realizam apenas capacidades registradas; a resposta deve refletir o resultado real do executor.

## 2. Primeira entrega nesta branch

- `anpes.py`: validação de plano versionado, limite de oito etapas, IDs únicos, catálogo explícito de ferramentas, classificação de risco, simulação padrão, exigência de aprovação explícita para ações que não sejam de baixo risco, interrupção após falha e eventos de auditoria sem traceback exposto.
- `test_anpes.py`: testes de formato, limites, ferramenta desconhecida, IDs duplicados, aprovação, simulação, executor ausente, falha e sanitização de erro.
- O módulo não usa `eval`, não executa shell, não carrega código proposto dinamicamente e não se reescreve.

## 3. Limites desta entrega

A política de autorização do ANPES está conectada ao caminho existente do `StacyOrchestrator`: `autonomy.py` delega ao ANPES preservando o contrato anterior. O orquestrador agora executa planos por um runtime restrito com dois handlers reais: diagnóstico de estado e delegação de intenções que já passaram pelo gate determinístico do CORE. As ações atuais de tarefas/memória passam pelo executor ANPES sem substituir os handlers funcionais existentes. **As ferramentas genéricas de Android, alteração de código, testes acionados pelo app e auto-modificação não estão registradas como executores operacionais.** A integração continua dependente do Termux e precisa de validação no aparelho.

O teste automatizado não substitui compilação Android nem teste físico. A branch não deve ser mesclada nem o APK declarado final por causa desta entrega isolada.

## 4. Fases de implementação

### Fase A — Contrato e validação (esta etapa)
- [x] Definir o contrato de plano e o catálogo inicial de ferramentas.
- [x] Limitar número de etapas e rejeitar ferramentas não registradas.
- [x] Exigir aprovação para ferramentas de risco médio, alto ou crítico.
- [x] Simulação padrão e tratamento seguro de falha.
- [ ] Executar a suíte completa Python e confirmar CI no commit desta branch.

### Fase B — Integração com o CORE
- [x] Inspecionar e escolher o ponto único do gate de autonomia existente.
- [x] Delegar o gate histórico ao ANPES preservando o contrato público de `autonomy.py`.
- [x] Adicionar consulta determinística de estado do ANPES ao `StacyOrchestrator`.
- [x] Registrar executores restritos para diagnóstico e intenções autorizadas pelo CORE.
- [x] Encaminhar intenções de tarefa/memória pelo executor ANPES, preservando handlers legados e respostas.
- [x] Adicionar testes de integração do runtime ANPES.
- [ ] Ligar ferramentas genéricas Android e outras capacidades uma a uma.
- [ ] Testar regressão, ações pendentes, concorrência e recuperação de sessão no aparelho.

### Fase C — Painel Núcleo STACY
- [ ] Mostrar estado real do CORE/ANPES, tarefas, aprovações, testes e histórico.
- [ ] Diferenciar “planejado”, “aguardando aprovação”, “executando”, “concluído” e “falhou”.
- [ ] Não mostrar botão ou indicador como operacional antes de conectar sua ação.

### Fase D — Laboratório de aprimoramento
- [ ] Criar área isolada para propostas de alteração e testes.
- [ ] Exigir revisão de diff, testes, verificação de segurança e plano de rollback.
- [ ] Separar propor, aplicar, compilar, testar e publicar como permissões distintas.
- [ ] Nunca permitir que o modelo altere políticas de segurança, permissões ou os próprios validadores sem revisão explícita.

### Fase E — Android autônomo e distribuição
- [ ] Ampliar integrações Android individualmente e validar permissões no aparelho.
- [ ] Planejar migração do CORE para dentro do APK; hoje a integração depende do Termux e de `$HOME/stacy`.
- [ ] Validar instalação, dados persistentes, voz, assistente padrão/botão lateral, atualização e rollback em dispositivo físico.

## 5. Critérios de aceite

- Plano inválido ou ferramenta não registrada nunca executa.
- Simulação não chama executores.
- Ações fora de baixo risco não executam sem aprovação explícita por etapa.
- Falha de um executor interrompe o plano e não declara sucesso.
- Resultado final corresponde ao retorno do executor; não se presume sucesso.
- Toda integração real tem testes automatizados e teste de regressão.
- Mudanças são feitas em branch separada, com backup preservado e CI verde antes de qualquer merge.
- RBI registra commit, resultados de CI, APK gerado e validação em dispositivo quando disponível.

## 6. Estado atual

**Em implementação — runtime restrito integrado ao CORE.** O gate, a consulta de estado e a execução de intenções autorizadas usam o ANPES; a CI desta atualização ainda precisa ser executada. Nenhuma afirmação de autonomia plena, integração Android concluída ou APK autossuficiente é feita neste relatório.
