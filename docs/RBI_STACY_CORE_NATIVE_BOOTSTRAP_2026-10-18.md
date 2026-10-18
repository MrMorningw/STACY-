# RBI — Bootstrap do STACY Core Native
Data: 18 de outubro de 2026

## Objetivo
Criar um caminho de resposta Android nativo, determinístico e leve que possa ser testado sem Termux, Python, HTTP localhost ou rede. Preservar o CORE Python para solicitações que ainda dependem do Orchestrator existente.

## Backup
- Branch de segurança: `backup/stacy-pre-native-core-2026-10-18`
- Commit preservado: `39da66b7b76abf39b9e6d0a6e279961b2fa7d809`
- O backup aponta para o estado de `main` imediatamente anterior ao início desta migração.

## Implementado nesta etapa
1. Adicionado `StacyNativeCore.kt`, um motor Kotlin sem dependências de rede.
2. O caminho nativo atende saudações e comandos explícitos de teste/diagnóstico.
3. A resposta nativa passa por `CoreResultStore`, o mesmo canal que alimenta a ViewModel, a resposta visual e a voz.
4. A ponte não inicia Termux no construtor; só solicita o runtime externo quando a mensagem não é atendida pelo caminho nativo.
5. O script de inicialização tem um atalho para evitar sincronização/download redundante quando o mesmo código do app já possui um CORE saudável.
6. Mensagens não reconhecidas continuam para o CORE Python existente; a migração não o substitui nesta etapa.
7. Adicionados testes unitários do motor nativo e testes de regressão do contrato Android.

## Prova de funcionamento proposta
Enviar na caixa de conversa:
- `Teste de comunicação sem Termux`
- `Olá, STACY`
- `Olá, STACY. Responda apenas: Estou funcionando, senhor.`

O diagnóstico nativo identifica explicitamente que não utilizou Termux e que não testou o Orchestrator Python/IA generativa.

## Limites conhecidos
Este bootstrap não é um substituto completo de uma IA generativa e ainda não migra memória persistente, entidades, agentes, pesquisa, tarefas ou ferramentas Python para Kotlin. Solicitações fora do escopo nativo seguem o caminho antigo enquanto a migração gradual continua.

## Critérios de validação
- Android CI: compilação e testes unitários passam.
- Testes de regressão Python: contrato da ponte e versão atualizados.
- Validação física: enviar as mensagens acima no aparelho e confirmar o retorno na interface. O CI não substitui esse teste em dispositivo real.

## Estratégia de rollback
Se a nova etapa falhar, manter `main` inalterada e reverter para `backup/stacy-pre-native-core-2026-10-18`. Integrar à linha principal somente após validação do CI.
