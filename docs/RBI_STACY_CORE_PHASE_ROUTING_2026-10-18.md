# RBI — Correção de roteamento de fases do CORE STACY
Data: 18 de outubro de 2026

## Objetivo
Corrigir a associação entre eventos de fase do núcleo Python e a requisição Android que originou esses eventos, evitando que requisições simultâneas troquem o identificador usado para atualizar a animação da STACY.

## Diagnóstico confirmado no código
O servidor usa `ThreadingHTTPServer`, portanto trata requisições em threads. Antes desta alteração, `CoreRuntime.chat` armazenava o identificador em `self.execution_id`, um campo compartilhado pelo objeto runtime. Duas requisições simultâneas poderiam sobrescrever esse campo e fazer `_phase` transmitir um identificador diferente daquele associado ao processamento que emitiu a fase.

## Correção implementada
1. Criado `core_phase_context.py`, com contexto local por thread e restauração/limpeza segura do identificador.
2. `CoreRuntime._phase` passa a consultar o contexto da thread que está processando a requisição.
3. O evento inicial `pensando` é emitido somente depois que a requisição adquire o lock serializador do CORE.
4. Incluído `core_phase_context.py` no grafo de arquivos sincronizados pelo daemon Termux, para que a cópia instalada em `~/stacy` receba o novo módulo.
5. Adicionados testes para isolamento entre threads, limpeza após exceção e restauração de contexto aninhado.
6. Atualizada a versão Android para `0.3.2` / versionCode `23`, para permitir atualização da instalação existente.

## Relação com app e animações
Os eventos `pensando`, `pesquisando` e `executando` continuam passando pelo receiver Android com validação do ID da execução ativa. Esta correção protege a associação do evento no servidor antes de chegar ao receiver; os resultados continuam trafegando pelo caminho já existente `CoreResultStore → MainActivity → WebView`.

## Validação
- Testes unitários de isolamento por thread incluídos.
- Testes de contrato exigem que o módulo novo seja sincronizado para o Termux e verificam o uso do contexto por requisição.
- O CI da branch precisa terminar com sucesso antes da integração.
- A interação ponta a ponta e a animação precisam ser verificadas no aparelho físico; compilação e testes automatizados não substituem essa verificação.

## Limites
Esta alteração corrige uma causa real de eventos de fase trocados. Ela não transforma, sozinha, todos os comandos em execução nativa nem substitui a IA generativa, o orquestrador Python ou a dependência de rede/API utilizada pelo CORE atual.

## Rollback
A alteração está isolada na branch `fix/stacy-core-phase-routing-0-3-2`. O backup pré-migração previamente preservado permanece disponível em `backup/stacy-pre-native-core-2026-10-18`.
