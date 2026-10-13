# RBI — Auditoria preliminar do STACY CORE
**Data:** 2026-10-13  
**Escopo:** núcleo Python, persistência local, ponte Android, fluxo de resposta e configuração do repositório.  
**Natureza:** auditoria estática da versão versionada; não substitui testes dinâmicos nem validação em dispositivo físico.

## 1. Preservação antes da auditoria

- **Commit auditado:** `5b322202ad9d3f3e6c948b5c83d40dfd85628776`
- **Backup imutável desta etapa:** `stacy-core-backup-20261013`, criado apontando para o commit acima.
- **Branch de trabalho deste relatório:** `stacy-core-audit-20261013`.
- **PR #23:** permanece aberto; nenhuma alteração foi feita na `main` durante esta auditoria.
- **CI do commit auditado:** os workflows de testes Python, CI principal, MP-10, MP-11, Final CI e Android CI reportaram sucesso. A execução Android CI #181 (run `38343124949`) concluiu o job de compilação e testes unitários com sucesso e publicou o artefato de APK de debug. Isso comprova a compilação e os testes executados pelo pipeline, não a operação em aparelho real.

## 2. Resumo executivo

A base tem boas medidas iniciais: protocolo JSON separado de diagnósticos, parser determinístico de ações Android com lista permitida, gravação atômica do estado conversacional, bloqueio exclusivo entre processos para a sessão, e leitura da chave Gemini fora do código-fonte.

**Conclusão preliminar:** não é seguro declarar o núcleo pronto para migração ou distribuição ainda. Há riscos concretos na persistência dos dados, no isolamento do WebView e no tratamento de falhas da ponte. Recomenda-se corrigir os riscos P1 antes de iniciar a migração para Python incorporado/Kotlin nativo. Nenhum código-fonte foi modificado nesta auditoria.

## 3. Achados priorizados

### P1 — Dados operacionais e pessoais versionados no Git
**Evidência:** `.gitignore` não exclui `memory.json`, `entities.json` ou `tasks.json`. Os três arquivos estão rastreados no commit auditado e contêm registros, não apenas estruturas vazias.

**Risco:** alterações de memória, entidades e tarefas feitas em execução podem aparecer como alterações Git; backups, clones e branches podem replicar dados pessoais. Também há risco de conflito entre estado de execução e atualização do repositório.

**Correção recomendada:** primeiro fazer uma cópia local segura dos dados existentes; depois mover o armazenamento operacional para diretório privado de dados do aplicativo (ou diretório privado dedicado do usuário durante a fase Termux), adicionar os arquivos de dados ao `.gitignore`, removê-los do rastreamento sem apagar as cópias locais e validar a migração com fixtures de teste. Não apagar os registros existentes nem alterar o formato sem um plano de migração testado.

### P1 — WebView com JavaScript bridge sem política explícita de navegação
**Evidência:** `MainActivity.kt` habilita JavaScript, ativa acesso a arquivos, registra `StacyJsBridge` com `addJavascriptInterface` e usa um `WebViewClient()` padrão sem uma allowlist explícita de navegação no código inspecionado.

**Risco:** se conteúdo remoto ou uma navegação inesperada for carregada no mesmo WebView, scripts dessa página podem tentar chamar os métodos expostos pela bridge, incluindo envio de mensagens ao núcleo e acionamento de atualização/configurações.

**Correção recomendada:** permitir no WebView apenas o asset local esperado; abrir links externos no navegador do sistema; rejeitar esquemas e destinos inesperados; desativar acesso a arquivos/conteúdo quando não necessário; validar e limitar todos os argumentos da bridge. Adicionar testes para navegação externa e URLs malformadas.

### P2 — Persistência de memória, entidades e tarefas não é atômica
**Evidência:** `memory.py`, `entity_store.py` e `tasks.py` escrevem diretamente nos arquivos JSON. O estado de sessão em `android_session.py` tem gravação atômica e lock, mas esses outros stores não usam o mesmo mecanismo.

**Risco:** encerramento durante a gravação pode deixar JSON truncado; acessos concorrentes por diferentes entradas (CORE, CLI ou widgets) podem sobrescrever alterações. Em alguns caminhos, JSON inválido resulta em estrutura vazia, o que pode parecer perda de dados.

**Correção recomendada:** criar uma camada de armazenamento única com escrita temporária + fsync + replace, validação de esquema, backup rotativo e lock compartilhado. Considerar SQLite com transações e migrações para o armazenamento persistente. Ao detectar corrupção, preservar o arquivo inválido e informar a recuperação em vez de tratá-lo silenciosamente como memória vazia.

### P2 — A ponte pode ficar aguardando indefinidamente
**Evidência:** `StacyCoreBridge` mantém uma fila serializada e só libera a próxima requisição quando o receiver conclui/falha. Não foi identificado timeout explícito por execução nem recuperação da fila para o caso de o Termux aceitar o serviço e nunca devolver o callback.

**Risco:** uma execução travada pode impedir todas as mensagens seguintes até a recriação do processo ou da Activity.

**Correção recomendada:** adicionar timeout cancelável por execução, estados de falha definidos, liberação idempotente da fila e teste de callback ausente/duplicado. O timeout não deve repetir automaticamente uma ação potencialmente não idempotente.

### P2 — Mensagens de erro podem expor detalhes internos
**Evidência:** em `StacyCoreResultReceiver.kt`, quando o código de saída não é zero, o texto completo de `stderr` é encaminhado à função de erro da interface. Esse canal pode conter caminhos locais, comandos ou tracebacks.

**Risco:** detalhes de implementação podem ser apresentados ao usuário e potencialmente expostos em capturas ou registros.

**Correção recomendada:** exibir uma mensagem segura e curta ao usuário; conservar diagnósticos técnicos em log local restrito, com redação de segredos e limites de tamanho. Não enviar chaves ou conteúdo sensível para logs.

### P2 — Validação do estado de sessão é apenas parcialmente estrutural
**Evidência:** `android_session.py` valida o esquema e tipos de nível superior, mas aceita dicionários arbitrários para ação pendente, decisão, entidade contextual e conteúdo de cada item do histórico.

**Risco:** estado local malformado pode ser aceito e causar falhas inesperadas em módulos posteriores. O arquivo de sessão também não tem limite de tamanho total explícito.

**Correção recomendada:** definir esquemas estritos por campo, limites de tamanho e comprimento, versão de migração e regras explícitas para ações pendentes. Revalidar autorização e confirmação no momento da execução; nunca confiar apenas em uma ação restaurada.

### P3 — Chamada interna do orquestrador acopla a ponte à implementação
**Evidência:** `android_core.py` chama o método privado `_registrar_resultado_conversa` para registrar uma ação Android.

**Risco:** mudanças internas no orquestrador podem quebrar a integração sem que o contrato público indique a alteração.

**Correção recomendada:** criar um método público/documentado ou um contrato de resultado tipado e cobri-lo com teste de integração.

### P3 — Dependência do Termux ainda está codificada na ponte
**Evidência:** `StacyCoreBridge` verifica o pacote `com.termux`, chama `RunCommandService` e pressupõe o checkout Python em `$HOME/stacy`.

**Risco/impacto:** instalação, permissões de comandos externos, Python, dependências e caminho do repositório são pré-requisitos operacionais; isso não é um defeito inesperado, mas o limite arquitetural atual.

**Correção recomendada:** não remover essa ponte antes de construir e testar uma alternativa. Para a primeira migração, avaliar compatibilidade real do Chaquopy com as dependências; manter fallback/branch reversível; comparar respostas e persistência entre a implementação atual e a nova.

## 4. Controles já presentes

- Saída do CORE em um objeto JSON por linha e diagnósticos separados em stderr.
- Parser Android determinístico, com pacotes allowlisted e sem execução de shell arbitrária gerada pelo modelo.
- Bloqueio exclusivo e gravação atômica para o estado de sessão conversacional.
- Configuração de chave Gemini fora do código versionado, com permissões restritas no fluxo documentado.
- Fila para ordenar requisições e resultado estruturado para ações Android.
- Testes unitários de parser, protocolo JSON, continuidade da sessão e estado corrompido.
- CI Android executada com sucesso no commit auditado.

Esses controles reduzem riscos específicos, mas não comprovam a segurança ou a confiabilidade de ponta a ponta.

## 5. Plano seguro de correção

1. Preservar o backup atual e confirmar que ele permanece apontado ao commit auditado.
2. Criar fixtures sintéticas para memória, entidades e tarefas; não usar dados pessoais reais nos testes.
3. Corrigir P1: tirar arquivos operacionais do rastreamento Git com migração não destrutiva e restringir navegação/bridge do WebView.
4. Fortalecer persistência JSON ou migrar para SQLite com testes de migração e rollback.
5. Implementar timeout/recuperação idempotente da fila e redação de erros.
6. Tornar a validação de sessão estrita e documentar o contrato público do CORE.
7. Rodar todos os testes Python e Android no mesmo commit; revisar diff e CI.
8. Instalar o APK em dispositivo real e validar mensagens sequenciais, concorrência, estado corrompido, permissões, voz, botão lateral, pesquisa e ações nativas.
9. Somente depois comparar o núcleo atual com a versão incorporada, sem substituir a implementação estável antes de evidências suficientes.

## 6. Critérios de aceite para encerrar a auditoria

- [ ] Arquivos de memória/tarefas reais não são mais versionados nem removidos durante a migração.
- [ ] Testes provam que JSON/SQLite sobrevive a encerramento durante gravação e acesso concorrente.
- [ ] WebView bloqueia navegação remota no contexto que contém a bridge.
- [ ] Nenhuma falha ou timeout deixa a fila permanentemente bloqueada.
- [ ] Erros mostrados na UI não contêm traceback, caminho interno, chave ou dados privados.
- [ ] Estado restaurado é validado por esquema e ações pendentes não são repetidas sem autorização.
- [ ] CI verde no commit final e testes em aparelho real documentados.
- [ ] O backup continua intacto e o rollback foi ensaiado antes de qualquer integração à `main`.

## 7. Limitações desta auditoria

Foi feita leitura estática dos arquivos versionados e verificação do resultado dos workflows no GitHub. Não foram executados fuzz tests, testes de penetração, análise de dependências, testes de carga, inspeção de APK instalado, nem testes no aparelho do usuário. O resultado é uma auditoria preliminar baseada em evidências do código, não uma certificação de ausência de falhas.
