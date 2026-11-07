# STACY 0.4.5 — auditoria, especificação detalhada e matriz de validação

**Base auditada:** main em 7e93ab2d09fba1926c49aa91dc835ed9ec3b5e03 (2026-11-03)  
**Branch de trabalho:** work/stacy-0.4.5-package-implementation  
**Versão atual de referência:** 0.4.4 / versionCode 34  
**Versão planejada:** 0.4.5 / versionCode 35 (confirmar no build antes de qualquer release)  
**Regra de release:** não publicar APK, manifesto ARS ou release até concluir testes automatizados, regressão, conferência de assinatura e validação em aparelho Android.

Este documento é a especificação de trabalho e de aceite da 4.5. Os itens abaixo são requisitos a implementar e verificar, não funcionalidades já concluídas. A meta é reduzir omissões e tornar cada aprovação rastreável. Não existe garantia honesta de ausência absoluta de falhas; a liberação depende das evidências definidas nesta matriz.

---

## 0. Escopo fechado e princípios obrigatórios

### Frentes do pacote
1. Desempenho, confiabilidade e comunicação Gemini/CORE.
2. Identificação verdadeira do estado da chave e da conexão API.
3. Histórico permanente de conversas.
4. Gerenciamento, abertura, exclusão e limpeza de conversas.
5. Navegação Android por gestos, retorno hierárquico e acessibilidade funcional.
6. Testes, integração, regressão, segurança, release e validação física.

### Princípios de implementação
- Trabalhar exclusivamente na branch de pacote; manter main e a instalação 0.4.4 sem alterações.
- Fazer alterações pequenas e rastreáveis dentro da mesma branch; agrupar a entrega em um único ciclo 4.5.
- Não mudar a identidade visual já aprovada: fundo preto, laranja, átomo/orbe, tipografia, animações e composição.
- Priorizar a arquitetura existente: interface HTML em WebView, ponte JavaScript/Android e CORE Kotlin.
- Não criar dois históricos concorrentes entre WebView, ViewModel e SQLite. Definir uma única fonte de verdade persistente.
- Não registrar chave API, prompts privados ou conteúdo integral de conversas em logs de diagnóstico.
- Não declarar conexão, resposta, persistência, build ou publicação como bem-sucedidos sem evidência verificável.
- Não sacrificar precisão, contexto ou integridade das respostas apenas para atingir um cronômetro.
- Tratar pesquisa web, conversas comuns e comandos locais como perfis operacionais distintos.
- Preservar tarefas, memórias, preferências e dados locais existentes durante qualquer migração.
- Todo erro deve terminar em estado visível e recuperável; não deixar bolhas pendentes, indicadores presos ou operações silenciosamente abandonadas.

### Estados de execução do pacote
- NÃO INICIADO: requisito ainda não implementado.
- EM IMPLEMENTAÇÃO: código alterado, sem aceite.
- EM TESTE: implementação concluída, evidências sendo coletadas.
- APROVADO: todos os testes e critérios daquele requisito passaram.
- BLOQUEADO: depende de correção ou decisão.
- NÃO APLICÁVEL: justificativa registrada.

No momento da criação desta matriz, a auditoria e o planejamento estão registrados; as implementações funcionais da 4.5 ainda não foram aprovadas.

---

## 1. Auditoria técnica de referência

### Arquivos e responsabilidades observados
- StacyAiClient.kt: transporte HTTP para Gemini, montagem do payload, timeouts, tentativas, extração de texto/fontes e contexto de interação.
- StacyCoreBridge.kt: roteamento de mensagens, comandos locais, chamada ao cliente Gemini, publicação de estados, resultados e teste de conexão.
- StacySecretStore.kt: armazenamento seguro da chave e identificador de interação anterior.
- MainActivity.kt: ciclo Android, WebView, ponte JavaScript, diálogo de configuração da IA, resposta, voz e automações.
- StacyViewModel.kt: estado Compose e lista de mensagens em memória.
- StacyLocalStore.kt: SQLite atual para tarefas e memórias.
- stacy_prototipo36.html: interface real do WebView, menu lateral, páginas internas, envio, bolhas pendentes, animações e configurações.
- AndroidManifest.xml e build.gradle.kts: permissões, Activity, serviços, SDK, versão e dependências.
- workflows e testes em androidTest: build, validações JavaScript, transporte Gemini e ponte WebView.

### Achados concretos
- O cliente Gemini utiliza executor de thread única; uma chamada lenta pode atrasar outras solicitações enfileiradas.
- O timeout de conexão está em 10 segundos; leitura de chat em 45 segundos e pesquisa em 60 segundos.
- Há até quatro tentativas HTTP. O atraso de retry é adicionado ao tempo da requisição e não há orçamento global que cubra fila, conexão, geração, retries, ponte e renderização.
- O cliente mantém um identificador de interação anterior no armazenamento seguro; hoje ele é global, não isolado por conversa.
- O teste de conexão chama o mesmo fluxo de chat e, na implementação observada, pode usar/atualizar o identificador de contexto usado pelas conversas. Isso precisa ser isolado para não contaminar o contexto.
- A interface HTML utiliza watchdog de aproximadamente 70 segundos, acima da meta de experiência definida para conversas comuns.
- A mensagem de retry apresenta attempt/3, enquanto a política permite quatro tentativas totais; conferir nomenclatura para não confundir tentativas totais com retries adicionais.
- StacyViewModel mantém mensagens em memória. StacyLocalStore guarda tarefas e memórias, mas não há tabelas de sessões e mensagens.
- A página Conversas do HTML ainda é um placeholder que solicita o histórico ao CORE; não lista, abre nem exclui sessões persistidas.
- O menu lateral e as páginas são controlados por JavaScript. MainActivity não apresenta tratamento explícito de back coordenado com essa navegação.
- A Activity possui configuração de IA e fluxo Salvar e testar. É necessário separar confirmação do armazenamento seguro de confirmação da conexão remota.
- O workflow da versão 0.4.4 aprovado é evidência apenas da base anterior, não da 4.5.

---

## 2. Frente A — Desempenho e confiabilidade Gemini/CORE

### A1. Definição mensurável de desempenho
- Medir o tempo ponta a ponta desde o toque em Enviar até a resposta final ser apresentada na bolha da conversa.
- Usar relógio monotônico no Android (por exemplo, elapsedRealtimeNanos/System.nanoTime), não relógio civil sujeito a ajustes.
- Registrar separadamente:
  1. envio do toque e criação da mensagem;
  2. entrada e espera na fila;
  3. preparação do payload;
  4. DNS/conexão/TLS quando mensurável;
  5. envio do corpo;
  6. espera pelo primeiro byte/resposta do servidor;
  7. leitura completa;
  8. parsing e extração de texto;
  9. retorno da ponte Kotlin;
  10. atualização e renderização da WebView.
- Calcular tempo total, média, mediana, percentil 90 e percentil 95 em testes repetidos.
- Separar resultados por perfil: comando local, conversa simples, conversa longa, pesquisa web e teste de conexão.
- Definir o orçamento de 10 segundos para conversa comum em condições normais de rede e serviço. Meta operacional recomendada: percentil 95 de até 10 segundos no conjunto controlado de prompts simples.
- Não aplicar a mesma meta rígida a pesquisas web e tarefas complexas; esses fluxos devem ter orçamento próprio, progresso explícito e possibilidade de cancelamento.
- Não computar a animação mínima da interface como tempo de geração do Gemini; apresentar separadamente latência técnica e tempo visual.
- Não esconder timeout, erro ou resposta incompleta para fazer a métrica parecer aprovada.

### A2. Perfil de solicitação
- Criar classificação explícita e auditável entre:
  - comandos locais determinísticos;
  - conversa comum;
  - pergunta que exige resposta mais elaborada;
  - pesquisa web/fato atual;
  - teste de conectividade.
- A classificação não pode depender apenas de palavras ambíguas como “hoje” ou “agora” sem considerar intenção e contexto.
- Conversa comum não deve ativar Google Search sem necessidade.
- Pesquisa web deve ativar a ferramenta apenas quando solicitada ou necessária para informação atual/verificável.
- Mostrar visualmente o estado pesquisar apenas quando a pesquisa estiver realmente ativa.
- O modo de teste de API deve ser isolado do histórico normal.
- Criar parâmetros de geração específicos por perfil, medidos por benchmark. Avaliar thinking_level e max_output_tokens; não manter limite de 32.768 tokens indiscriminadamente se isso aumentar a latência ou permitir respostas excessivamente longas.
- Definir limites adaptativos por tipo de tarefa sem truncar arbitrariamente respostas essenciais.
- Respostas simples devem ser objetivas; pedidos complexos devem preservar a qualidade e sinalizar quando exigirem mais tempo.

### A3. Orçamento total e timeouts
- Implementar deadline absoluto por solicitação comum, contado desde a entrada na fila, e não reiniciado a cada tentativa.
- Orçamento de 10 segundos inclui fila, conexão, escrita, leitura, parsing e entrega à interface.
- Configurar timeout de conexão e leitura compatíveis com o deadline restante; nenhuma etapa deve poder exceder o orçamento total.
- Quando o deadline terminar, cancelar a operação local, fechar a conexão HTTP e publicar um resultado terminal de timeout.
- Evitar que o cancelamento local seja descrito como cancelamento garantido do processamento remoto.
- Implementar orçamento separado e claramente comunicado para pesquisa web, com progresso e cancelamento.
- O teste de conexão deve ter timeout curto e independente.
- Garantir que uma solicitação expirada não possa publicar uma resposta tardia sobre uma solicitação mais nova.
- Criar identificador único por solicitação e ignorar callback de execução cancelada, duplicada ou obsoleta.
- Tratar interrupção de thread de forma correta e não engolir InterruptedException sem restaurar o estado de interrupção.

### A4. Fila, concorrência e contexto
- Auditar o executor de thread única e medir o tempo de espera que ele introduz.
- Evitar fila global ilimitada.
- Definir política explícita de solicitações simultâneas: no máximo uma geração em andamento por conversa/contexto, para preservar a ordem e a cadeia de previous_interaction_id.
- Permitir isolamento entre conversas diferentes sem misturar seus contextos.
- Limitar concorrência total do aplicativo para proteger memória, bateria e limites da API.
- Definir comportamento ao enviar várias mensagens rapidamente: bloquear envio, enfileirar com limite ou cancelar a anterior; nunca duplicar nem perder silenciosamente.
- Definir o que ocorre ao iniciar pesquisa enquanto há conversa em andamento.
- Definir o que ocorre ao sair da conversa, alternar sessão, fechar o app ou destruir a Activity durante uma solicitação.
- A mudança de sessão deve impedir que resposta da sessão anterior apareça na sessão atual.
- A atualização de interface deve estar ligada ao requestId e conversationId corretos.
- Operações locais rápidas não devem ficar atrás de uma chamada Gemini lenta.

### A5. Política de retry
- Não repetir automaticamente erros determinísticos como chave inválida, permissão negada, payload inválido ou modelo/recurso inexistente.
- Repetir somente falhas transitórias que tenham política definida, como timeout de transporte, HTTP 408 e determinados HTTP 5xx.
- Para HTTP 429, distinguir limite transitório de taxa de cota/billing esgotada; não insistir em cota esgotada.
- Respeitar Retry-After sem ultrapassar o deadline total.
- Retry precisa caber no orçamento restante; se não couber, encerrar imediatamente com diagnóstico.
- Limitar número de tentativas e atraso acumulado; evitar quatro tentativas que consumam dezenas de segundos.
- Usar backoff e jitter apenas quando compatíveis com o tempo disponível.
- Não reiniciar a contagem de prazo ao repetir.
- Garantir que uma tentativa repetida preserve exatamente a mensagem, o perfil, o conversationId e o contexto aplicável.
- Não executar retry duplicado em duas camadas diferentes (cliente e CORE).
- Exibir status correto: tentativa atual, total de tentativas e próximo atraso; não confundir retries com chamadas totais.
- Testar interrupção durante o backoff, resposta durante cancelamento e esgotamento do prazo.

### A6. Integridade do protocolo e respostas
- Validar endpoint, método HTTP, cabeçalhos, content type e estrutura do payload.
- Confirmar compatibilidade do modelo configurado com o endpoint e a estrutura Interactions usada.
- Validar leitura de resposta HTTP de sucesso e erro sem perder o corpo diagnóstico.
- Tratar JSON vazio, malformado, campos ausentes, tipos inesperados e resposta sem texto.
- Distinguir queued, in_progress, requires_action, incomplete, completed e estados desconhecidos.
- Não considerar HTTP 2xx suficiente se a resposta não estiver concluída ou não contiver texto utilizável.
- Implementar ou rejeitar explicitamente requires_action; não apresentar esse estado como resposta normal.
- Tratar resposta parcial/incompleta sem fingir conclusão.
- Extrair texto e fontes sem duplicar parágrafos ou fontes.
- Validar URLs das fontes e não apresentar esquemas inseguros.
- Não reutilizar previous_interaction_id de outra conversa, conta ou chave.
- Limpar contexto obsoleto apenas quando o erro indicar que ele está expirado/inexistente; depois repetir no mesmo deadline somente se houver margem.
- Salvar o novo identificador de interação somente depois de uma resposta final válida.
- Não salvar um identificador obtido por teste de conexão na conversa do usuário.
- Proteger contra duplicação da resposta quando CoreResultStore, CorePhaseStore e WebView publicarem eventos próximos.

### A7. Erros e recuperação
- Mapear mensagens claras para: sem internet, DNS, conexão recusada, TLS/certificado, timeout, HTTP 400, 401, 403, 404, 408, 429, 5xx, resposta vazia, JSON inválido e serviço ainda processando.
- Mostrar orientação proporcional ao erro, sem expor stack trace ou segredo.
- Não informar “offline” quando apenas a IA remota está indisponível e comandos locais continuam ativos.
- Limpar o estado de processamento em todos os caminhos de sucesso, erro, exceção, cancelamento e destruição.
- Garantir que a bolha pendente seja substituída uma única vez.
- Garantir que o erro específico do CORE não seja sobrescrito por mensagem genérica da WebView.
- Permitir nova tentativa manual depois de erro recuperável.
- Não bloquear novos envios permanentemente após falha.
- Não converter falha em texto inventado para aparentar resposta adequada.

### A8. Instrumentação e privacidade
- Criar telemetria local de latência por etapa, status HTTP, perfil, contagem de tentativas e tipo de falha.
- Não registrar API key, cabeçalho x-goog-api-key, prompt, resposta integral, identificador privado de sessão ou dados pessoais.
- Usar IDs aleatórios efêmeros para correlacionar etapas.
- Definir retenção limitada dos logs e opção de diagnóstico sem conteúdo sensível.
- Não enviar telemetria para serviço externo sem decisão explícita e documentada.
- Criar relatório de benchmark com rede, aparelho, versão Android, modelo, tamanho do prompt, perfil e número de amostras.

### A9. Testes específicos do Gemini/CORE
- Sucesso rápido de conversa simples.
- Sucesso com resposta longa.
- Prompt em português com acentos, emojis e pontuação.
- Mensagem vazia ou só com espaços.
- Comando local sem rede.
- Pesquisa web solicitada explicitamente.
- Pergunta atual que exige pesquisa.
- Prompt normal que não deve disparar pesquisa.
- Resposta do servidor em menos de 10 s.
- Resposta do servidor acima de 10 s.
- Fila ocupada e deadline vencido antes da conexão.
- Duas mensagens rápidas na mesma conversa.
- Duas conversas independentes.
- Alternar de conversa enquanto a primeira responde.
- App enviado para segundo plano e restaurado.
- Activity recriada durante solicitação.
- HTTP 400, 401, 403, 404, 408, 429 transitório, 429 quota, 500, 502, 503 e 504.
- Retry-After em segundos e em data HTTP.
- Resposta 2xx incompleta, vazia ou malformada.
- Contexto anterior válido, expirado e inexistente.
- Interrupção durante retry e timeout.
- Verificar que não há callback tardio nem resposta duplicada.
- Repetir benchmark suficiente para calcular mediana e P95, com registro dos resultados.

**Critério de aceite A:** fluxo de conversa comum mede tempo ponta a ponta e atinge P95 de até 10 segundos em condições controladas e saudáveis; ao exceder o orçamento, termina com erro claro dentro do limite, sem congelar a interface, duplicar mensagens ou deixar estados pendentes. Pesquisa possui orçamento próprio. Nenhuma falha externa deve ser mascarada.

---

## 3. Frente B — Identificação real da chave e da conexão API

### B1. Modelo de estados
Implementar estados únicos e tipados:
- SEM_CHAVE: nenhuma chave armazenada.
- CHAVE_SALVA_NAO_VERIFICADA: segredo presente, conexão ainda não testada.
- VERIFICANDO: teste remoto em execução.
- CONECTADA: teste autenticado e válido concluído recentemente.
- ERRO_CHAVE: chave inválida, revogada ou sem permissão.
- ERRO_COTA: cota/billing/limite não recuperável.
- ERRO_REDE: sem rede, DNS, timeout ou TLS.
- ERRO_SERVICO: indisponibilidade remota.
- ERRO_DESCONHECIDO: erro não classificado.

### B2. Regras de verdade do indicador
- Chave salva não equivale a conexão confirmada.
- O estado CONECTADA só pode ser publicado após resposta válida do teste remoto.
- O texto de estado deve diferenciar “chave salva” de “serviço conectado”.
- Ao substituir ou apagar a chave, invalidar imediatamente o estado anterior.
- Ao ocorrer falha de autenticação, invalidar CONECTADA.
- Falha transitória de rede não deve apagar a chave salva, mas deve indicar que a conexão não pôde ser confirmada.
- Definir validade temporal do último teste; não apresentar como conectado indefinidamente com base em teste antigo.
- Ao reiniciar o app, recuperar o último diagnóstico como histórico, mas não alegar conexão atual sem verificação válida segundo a política de validade.
- Atualizar estado após falha de uma chamada normal, sem oscilar incorretamente durante erros isolados.
- Evitar múltiplos testes simultâneos; aplicar debounce e desabilitar o botão durante o teste.

### B3. Teste de conexão isolado
- Usar operação de health check específica, sem anexar previous_interaction_id da conversa.
- Não salvar o id da interação do teste como contexto de conversa.
- Não criar mensagem visível no histórico.
- Não misturar resposta do teste com conversa aberta.
- Usar deadline independente e payload mínimo que ainda valide autenticação e geração.
- Usar o mesmo modelo/endpoint da conversa para que o teste confirme a rota efetivamente usada.
- Mostrar sucesso apenas depois de validar status final e resposta útil.
- Distinguir sucesso de armazenamento local, sucesso de leitura da chave e sucesso remoto.

### B4. Interface no mesmo local da chave
- Preservar a tela/configuração atual e inserir o indicador junto da configuração da IA, sem criar tela desnecessária.
- Estados visuais: Conectada, Desconectada, Verificando, Chave salva — não verificada e erro.
- Exibir horário da última verificação quando útil.
- Botão com estados coerentes: Conectar, Testar conexão, Verificando, Reconectar.
- Desabilitar ações incompatíveis enquanto o teste está ativo.
- Não exibir a chave completa; usar campo mascarado ou estado “chave armazenada”.
- Não incluir chave API em histórico, notificações, logs, clipboard ou mensagens de erro.
- Garantir legibilidade, contraste, dimensionamento e acessibilidade do rótulo.
- O indicador precisa atualizar sem recarregar a WebView nem alterar o layout geral.

### B5. Armazenamento e rotação da chave
- Preservar Android Keystore/AES-GCM usado pelo SecretStore.
- Verificar leitura após salvar, tratamento de exceções e integridade do ciphertext.
- Ao trocar chave, limpar o previous_interaction_id antigo e invalidar a conexão.
- Ao apagar a chave, limpar contexto local associado e mudar estado imediatamente.
- Não permitir que uma operação iniciada com chave antiga atualize o status depois de uma rotação.
- Não imprimir nem devolver a chave por JavaScript bridge.
- Verificar política de backup; segredos não devem ser exportados em backup não protegido.
- Tratar Keystore indisponível, chave corrompida, restauração de backup e falha de descriptografia.
- Mensagem de erro deve instruir o usuário sem expor a chave.

### B6. Testes de API
- Sem chave.
- Chave salva e legível.
- Chave inválida.
- Chave revogada.
- Chave válida.
- Cota esgotada.
- Rate limit transitório.
- Sem internet.
- DNS falhando.
- Timeout.
- Servidor 5xx.
- Teste repetido rapidamente.
- Chave substituída durante teste.
- Chave apagada durante teste.
- Teste após reiniciar app.
- Verificar que teste não altera contexto da conversa e não aparece no histórico.
- Verificar que estado CONECTADA não persiste indevidamente após falha definitiva.

**Critério de aceite B:** indicador fiel, atualizado e acessível, com teste remoto isolado; nenhuma chave é exposta e nenhuma sessão é contaminada pelo health check.

---

## 4. Frente C — Histórico permanente de conversas

### C1. Fonte única da verdade
- Definir SQLite local como fonte persistente de sessões e mensagens.
- A interface HTML recebe operações e dados por uma ponte Android formal; não manter histórico paralelo apenas em DOM/localStorage.
- StacyViewModel deve observar ou receber snapshots do repositório, sem competir com o estado real exibido no WebView.
- Toda alteração de conversa deve passar pelo repositório, não por concatenação isolada no HTML.
- Estabelecer contrato de dados da ponte: listar sessões, criar sessão, abrir sessão, inserir mensagem, atualizar estado, excluir sessão e limpar tudo.
- Todas as respostas devem retornar conversationId e requestId para impedir mistura entre sessões.

### C2. Banco e esquema
- Criar migração versionada não destrutiva no banco existente.
- Tabela conversations/sessions com:
  - id estável (UUID);
  - título;
  - created_at;
  - updated_at/last_message_at;
  - last_message_preview;
  - estado da sessão, se necessário;
  - previous_interaction_id individual, tratado como dado sensível de contexto.
- Tabela messages com:
  - id estável;
  - conversation_id com chave estrangeira;
  - role (user/assistant);
  - texto;
  - timestamp;
  - sequência monotônica por sessão;
  - requestId;
  - estado (pending/completed/failed/interrupted);
  - metadados limitados de fontes e tipo de resposta, se usados pela interface.
- Índices para conversa por atualização, mensagens por conversation_id e sequência.
- Ativar foreign_keys e definir ON DELETE CASCADE para mensagens da sessão.
- Definir transações para criação de sessão + primeira mensagem e para operações em lote.
- Definir limite ou política de paginação para históricos muito longos.
- Tratar texto vazio, corpo muito grande, caracteres Unicode, emojis, novas linhas e URLs.
- Evitar armazenar campos redundantes que possam divergir.

### C3. Persistência do ciclo de mensagem
- Persistir mensagem do usuário antes de iniciar a chamada remota.
- Criar registro pending associado ao requestId.
- Ao receber resposta válida, persistir resposta do assistente e marcar request completed na mesma transação.
- Ao receber falha, registrar estado failed com diagnóstico seguro ou evento de erro separado, sem registrar segredo.
- Ao encerrar o processo com pedido pendente, marcar interrupted ao recuperar o banco; não deixar bolha girando eternamente.
- Atualizar last_message_at e preview após cada mensagem.
- Preservar ordem exata de envio e resposta.
- Impedir gravação duplicada quando callback chega duas vezes.
- Em caso de falha ao persistir resposta, não mostrar sucesso como se estivesse salva; tentar recuperação e informar o estado.
- Garantir que a bolha apresentada corresponde ao registro já persistido.
- Ao abrir conversa, carregar mensagens por ordem cronológica e restaurar rolagem ao final, salvo posição explicitamente preservada.

### C4. Contexto de sessão Gemini
- Cada conversa deve ter seu próprio previous_interaction_id.
- Remover dependência de um único ID global para múltiplas sessões.
- Ao enviar mensagem, usar apenas o ID associado à conversa selecionada.
- Atualizar o ID somente após resposta final válida daquela mesma sessão.
- Não usar o ID do health check.
- Não cruzar ID após criar nova conversa, excluir conversa ou alternar sessão.
- Ao migrar, não atribuir silenciosamente contexto remoto antigo a uma sessão diferente.
- Definir migração do ID global legado de forma conservadora e documentada.
- Se o ID legado não puder ser associado a um histórico local verificável, não inventar mensagens anteriores; informar que o histórico anterior à função não está disponível localmente.
- Ao ocorrer erro de contexto obsoleto, limpar somente o ID da sessão correspondente e recuperar conforme política.
- Ao trocar a API key, invalidar os contextos vinculados à chave anterior.

### C5. Retomada e continuidade
- Reabrir a última conversa ativa após reiniciar se essa for a experiência aprovada.
- Oferecer Nova conversa de forma explícita.
- Abrir sessão antiga e continuar nela com seu contexto correto.
- Criar sessão separada ao iniciar conversa nova.
- Não misturar solicitações de uma sessão com outra.
- Atualizar a lista de sessões sem perder a conversa aberta.
- Restaurar o conteúdo após rotação/recriação de Activity e processo morto.
- Não duplicar mensagem no retorno do Android.

### C6. Interface da seção Conversas
- Substituir o placeholder atual por lista real de sessões persistidas.
- Ordenar por atividade mais recente.
- Exibir título, prévia, data/hora e estado quando necessário.
- Gerar título a partir da primeira mensagem do usuário com limite de tamanho; não usar conteúdo sensível em cabeçalhos externos.
- Permitir abrir uma conversa.
- Permitir iniciar nova conversa.
- Mostrar estado vazio quando não houver sessões.
- Mostrar carregamento, erro de leitura e ação de tentar novamente.
- Paginar ou carregar incrementalmente quando houver muitas sessões.
- Manter estilo visual já aprovado, sem redesenhar a interface.
- Confirmar que o gesto lateral e botão Voltar funcionam também dentro da conversa aberta.

### C7. Integridade, privacidade e backup
- Avaliar criptografia do histórico local em repouso; se não for implementada na 4.5, registrar explicitamente a proteção efetiva e a limitação.
- Verificar android:allowBackup e regras de backup: decidir se conversas são incluídas, excluídas ou protegidas no backup.
- Não enviar histórico local inteiro ao Gemini sem necessidade; enviar apenas o contexto necessário da sessão.
- Não incluir histórico em logs, analytics ou relatórios automáticos.
- Definir política de retenção local e limites de armazenamento.
- Excluir corretamente registros relacionados e contextos locais.
- Esclarecer que apagar histórico local não significa necessariamente apagar interações armazenadas pelo provedor remoto; não prometer exclusão remota sem suporte confirmado.
- Garantir isolamento entre usuários/perfis Android quando aplicável.

### C8. Migração e compatibilidade
- Aumentar versão do esquema SQLite com migração incremental.
- Preservar tabelas tasks e memories.
- Testar upgrade partindo do banco real da 0.4.4.
- Testar instalação limpa.
- Testar banco vazio, banco parcialmente preenchido, versão antiga e falha no meio da migração.
- Fazer backup transacional quando necessário.
- Não apagar banco completo para recriar tabelas.
- Validar foreign keys, índices e contagem de registros após migração.
- Se migration falhar, não sobrescrever o banco original; apresentar erro controlado e permitir recuperação.
- Documentar a limitação: conversas que não foram salvas antes da 4.5 não podem ser reconstruídas localmente se nunca existiram no banco.

### C9. Testes de histórico
- Criar sessão e primeira mensagem.
- Salvar mensagem user e resposta assistant.
- Fechar e reabrir o app.
- Abrir conversa antiga e continuar.
- Criar segunda conversa e comprovar isolamento.
- Alternar entre duas conversas com resposta em andamento.
- Testar IDs de interação independentes.
- Reiniciar processo com mensagem pendente.
- Forçar falha de gravação e verificar consistência.
- Testar Unicode, emojis, acentos, textos longos e múltiplas linhas.
- Testar lista vazia, uma sessão e muitas sessões.
- Testar ordenação e prévia.
- Testar migração da 0.4.4.
- Verificar que tarefas e memórias continuam intactas.
- Verificar que health check não cria sessão ou mensagem.

**Critério de aceite C:** mensagens persistem após encerramento/reinício, sessões são recuperáveis e contextos Gemini isolados por conversa; migração não destrói dados preexistentes.

---

## 5. Frente D — Gerenciamento e exclusão de conversas

### D1. Operações disponíveis
- Criar nova conversa.
- Abrir conversa existente.
- Retomar conversa.
- Excluir uma conversa.
- Limpar todo o histórico.
- Atualizar lista após qualquer operação.
- Impedir ações sobre IDs inexistentes ou já excluídos.
- Operações devem ser idempotentes ou retornar estado explícito quando repetidas.

### D2. Exclusão individual
- Identificar a sessão selecionada pelo ID, nunca pelo título ou posição visual.
- Pedir confirmação com título suficiente para o usuário reconhecer a sessão.
- Excluir sessão e mensagens dependentes em transação.
- Remover contexto local Gemini correspondente.
- Se a sessão excluída estiver aberta, voltar para estado seguro e não publicar resposta tardia nela.
- Se houver solicitação ativa, cancelar localmente ou marcar como obsoleta antes de excluir.
- Não excluir qualquer outra sessão.
- Atualizar a lista depois do commit do banco, não antes.
- Tratar falha de banco sem remover a sessão visualmente como se tivesse sido apagada.
- Considerar opção de desfazer apenas se houver implementação segura; não é requisito obrigatório.

### D3. Limpeza total
- Solicitar confirmação explícita em duas etapas ou texto claro de irreversibilidade.
- Explicar o que será removido: sessões, mensagens e IDs de contexto locais.
- Não apagar tarefas, memórias, chave API, preferências ou configurações.
- Encerrar/cancelar solicitações ativas e invalidar callbacks pendentes.
- Executar limpeza transacional.
- Atualizar interface para estado vazio.
- Não limpar a chave Gemini por acidente.
- Não alegar que dados remotos do Google foram eliminados; informar que a operação limpa o histórico local, salvo se houver operação remota suportada e validada separadamente.

### D4. Testes de gerenciamento
- Excluir primeira, intermediária e última sessão.
- Excluir sessão aberta.
- Excluir sessão com solicitação ativa.
- Repetir exclusão do mesmo ID.
- Excluir sessão inexistente.
- Cancelar diálogo de confirmação.
- Confirmar limpeza total.
- Cancelar limpeza total.
- Falha no banco durante exclusão.
- Conferir que tarefas, memórias e chave API permanecem.
- Confirmar que lista e tela aberta refletem o banco depois da operação.

**Critério de aceite D:** exclusão individual e total são precisas, confirmadas e transacionais; nenhuma conversa não selecionada nem dado de outra área é perdido.

---

## 6. Frente E — Navegação por gestos Android e acessibilidade

### E1. Modelo de navegação
- Definir hierarquia explícita: menu lateral → página interna → detalhes/diálogos → conversa, conforme o estado real da interface.
- Gesto lateral do Android deve ser tratado pelo mecanismo nativo de back, não por detecção manual de swipe na WebView.
- Prioridade de retorno:
  1. fechar diálogo nativo/modal aberto;
  2. fechar menu lateral se estiver aberto;
  3. fechar subpágina interna e retornar à tela principal/orbe;
  4. voltar do detalhe da conversa à lista de conversas;
  5. voltar da lista para a tela principal, quando aplicável;
  6. somente quando não houver estado interno a recolher, permitir o comportamento padrão do Android.
- Não interpretar gesto de voltar como comando de encerrar em qualquer página interna.
- Não interceptar o gesto inferior de Home nem a navegação para Recentes.
- Não criar listener touch que dispute com o gesto preditivo do Android.
- Preservar retorno por botão físico/virtual Back onde disponível.

### E2. Integração nativa e WebView
- Usar OnBackPressedDispatcher/OnBackPressedCallback ou API compatível com a versão AndroidX usada.
- Avaliar suporte a predictive back no targetSdk 36 e manter o comportamento de animação nativa.
- Criar contrato explícito para a WebView informar estado do drawer, subpágina, diálogo e sessão/detalhe aberto.
- Manter o estado sincronizado entre JavaScript e MainActivity; evitar consulta assíncrona tardia que possa fechar o app por engano.
- Definir comportamento quando a WebView ainda não carregou ou foi destruída.
- Garantir que o callback não consuma Back sem ter um estado interno para recolher.
- Restaurar foco no elemento anterior após fechar painel ou página.
- Não alterar histórico de navegação do navegador por chamadas acidentais a loadUrl.
- Controlar Escape em teclado físico como equivalente a fechar modal/página quando aplicável.

### E3. Cenários de gesto
- Configurações → gesto lateral → retorna para tela do orbe.
- Conversas → abrir sessão → gesto lateral → retorna para lista.
- Conversas → lista → gesto lateral → retorna à home.
- Menu aberto → gesto lateral → fecha menu, sem encerrar app.
- Menu aberto sobre página interna → gesto lateral → fecha menu primeiro; segundo gesto volta página.
- Diálogo de API aberto → voltar fecha diálogo sem apagar chave.
- Campo de texto focado/teclado aberto → primeiro Back recolhe teclado conforme padrão Android; próximo Back navega.
- Pesquisa em andamento → voltar deve seguir política documentada e não perder resultado sem aviso.
- Voz ouvindo → voltar não deve deixar microfone/listener ativo indevidamente.
- Tela principal sem modal/página → Back segue comportamento padrão do app/Android.
- Swipe inferior para Home.
- Swipe inferior e pausa para Recentes.
- Gestos com navegação por três botões em aparelho de teste.
- Teste de gesto lateral partindo da borda esquerda e direita.
- Testar orientação, densidade e tamanhos de tela suportados.

### E4. Acessibilidade funcional
- Rótulos acessíveis em botões, menu, estado de conexão e ações de exclusão.
- Ordem de foco lógica ao abrir/fechar menu e subpágina.
- TalkBack deve anunciar títulos, estado e resultado das ações.
- Contraste suficiente para texto e estado; não depender apenas de cor para comunicar conexão/erro.
- Área de toque adequada em controles essenciais.
- Escala de fonte do Android sem cortar botões ou títulos.
- Navegação por teclado físico e foco visível, quando aplicável.
- Estados de carregamento comunicados a leitores de tela sem anúncios repetitivos.
- Não roubar foco da WebView após atualização de texto sem necessidade.
- Testar botão voltar em leitores de tela e com teclado aberto.

### E5. Testes de navegação
- Testes instrumentados da hierarquia de back.
- Testes de estado sincronizado JS ↔ Kotlin.
- Drawer aberto/fechado.
- Página interna aberta/fechada.
- Modal nativo aberto/fechado.
- Teclado visível/oculto.
- WebView em carregamento e destruída.
- Gesto lateral nos dois lados.
- Gesto inferior Home e Recentes.
- Predictive back em versão Android compatível.
- Teste em aparelho físico com navegação por gestos habilitada.
- TalkBack, fonte ampliada e teclado externo em smoke test.

**Critério de aceite E:** gesto lateral volta uma etapa interna apropriada sem fechar a STACY indevidamente; Home e Recentes permanecem sob controle do Android; foco e acessibilidade não são prejudicados.

---

## 7. Frente F — Integração, qualidade e regressão

### F1. Testes unitários
- Políticas de timeout e deadline.
- Política de retry e Retry-After.
- Classificação de erros HTTP.
- Extração de texto/fontes.
- Isolamento de conversationId e previous_interaction_id.
- Estados da conexão API.
- Migrações SQLite.
- Operações de sessão e mensagens.
- Exclusão individual e total.
- Estados de navegação.

### F2. Testes instrumentados
- Transporte Gemini com servidor falso.
- Bridge WebView/Android.
- Teste de conexão isolado.
- Persistência após recriação de Activity.
- Persistência após encerramento e reabertura.
- Migração do banco 0.4.4.
- Navegação de retorno e gestos.
- Estados visuais e mensagens de erro.
- Testes de ciclo de vida e callbacks tardios.

### F3. Regressão de recursos existentes
- Inicialização e tela principal com orbe atômico.
- Estados ONLINE, OUVINDO, PENSANDO, PESQUISANDO, EXECUTANDO, RESPONDENDO, OFFLINE e ERRO.
- Animações e preferência de animações.
- Entrada por teclado.
- Entrada por voz, permissão do microfone e reconhecimento de fala.
- Resposta falada/TTS e opção de silenciar.
- Comandos locais.
- Tarefas e conclusão de tarefas.
- Memória local e consulta de memória.
- Pesquisa web e apresentação de fontes.
- Ações Android autorizadas.
- Compartilhamento.
- Configurações.
- Permissões.
- Atualizador ARS.
- Comunicação WebView ↔ CORE.
- Rotação/recriação da Activity e retorno do segundo plano.
- Não deve haver regressão visual na composição ou no tamanho/alinhamento dos controles já aprovados.

### F4. Testes de robustez
- Sem internet/Modo avião.
- Wi-Fi instável e troca Wi-Fi/dados móveis.
- Perda de rede durante upload e download.
- API indisponível.
- Chave removida.
- App encerrado durante chamada.
- Processo morto pelo Android.
- Pouco espaço de armazenamento.
- Banco corrompido ou migração interrompida.
- Várias mensagens rápidas.
- Sessões longas e grande número de mensagens.
- Duplo toque em botões.
- Rotação e redimensionamento.
- Retorno rápido entre páginas.
- Repetição de teste de conexão.
- Memória e bateria sob carga.

### F5. Segurança e privacidade
- Confirmar que chave não aparece em tela, logs, exceptions, analytics ou histórico.
- Confirmar armazenamento seguro e tratamento de falha do Keystore.
- Confirmar que links, fontes e conteúdo remoto não são tratados como comandos privilegiados.
- Validar conteúdo recebido antes de executar ações Android.
- Não ampliar allowlist de aplicativos/ações fora do escopo.
- Validar JavaScript bridge e métodos expostos.
- Manter acesso a arquivos estritamente mediado pelo seletor.
- Confirmar configuração de backup para chave, conversas e banco.
- Conferir permissões do Manifest; não adicionar permissões desnecessárias.
- Testar instalação e atualização mantendo dados da versão anterior.

---

## 8. Plano de execução e gates de aprovação

### Gate 0 — Preparação
- Confirmar branch e commit base.
- Confirmar que main não foi modificada.
- Criar backup lógico/estado de referência para comparar dados existentes.
- Registrar baseline de latência da 0.4.4.
- Registrar screenshots de referência da interface atual.
- Confirmar testes disponíveis e lacunas.

### Gate 1 — Gemini/CORE
- Implementar deadline, fila, perfis, retry e telemetria.
- Executar testes A.
- Comparar benchmark com baseline.
- Aprovar somente com métricas e logs sanitizados.

### Gate 2 — API
- Implementar máquina de estados e health check isolado.
- Executar testes B.
- Verificar substituição/remoção de chave e isolamento de contexto.
- Aprovar somente após todos os estados testados.

### Gate 3 — Histórico
- Implementar migração e repositório único.
- Persistir sessões, mensagens e contextos por sessão.
- Integrar lista e abertura na WebView.
- Executar testes C.
- Aprovar somente após upgrade 0.4.4 sem perda de tarefas/memórias.

### Gate 4 — Gerenciamento
- Implementar exclusão individual e limpeza total.
- Executar testes D.
- Aprovar somente após prova de que dados não selecionados permanecem.

### Gate 5 — Navegação
- Implementar back nativo coordenado.
- Executar testes E em emulador e aparelho físico.
- Aprovar somente após teste real do gesto lateral e preservação de Home/Recentes.

### Gate 6 — Integração e regressão
- Executar toda a suíte, não apenas testes novos.
- Fazer instalação limpa e upgrade sobre 0.4.4.
- Verificar dados, aparência, voz, tarefas, memória, pesquisa e ARS.
- Corrigir falhas; repetir suíte após cada correção relevante.

### Gate 7 — Release candidato
- Atualizar versionName para 0.4.5 e versionCode para 35, confirmando que não há colisão.
- Executar assembleDebug, assembleRelease, testes unitários e instrumentados.
- Conferir packageName, minSdk, targetSdk, assinatura e certificado esperado.
- Calcular SHA-256 do APK.
- Conferir que o manifesto ARS aponta para o APK exato, versão e hash corretos.
- Não publicar automaticamente versão candidata sem aprovação de todos os gates.
- Não confundir artefato debug, release assinado, publicação ARS e instalação física.

### Gate 8 — Validação no aparelho do usuário
- Instalar sobre a versão 0.4.4 sem desinstalar previamente.
- Confirmar versão 0.4.5 e integridade do pacote.
- Testar conexão API no mesmo local de configuração.
- Testar conversa simples com cronômetro.
- Testar pergunta mais elaborada e pesquisa.
- Abrir, fechar e retomar conversas.
- Reiniciar aplicativo e aparelho.
- Excluir uma conversa e depois limpar o histórico com confirmação.
- Navegar por Configurações, Conversas e páginas internas usando gesto lateral.
- Testar Home e Recentes com gesto inferior.
- Testar voz, tarefas, memória, animações e comandos já existentes.
- Registrar evidências e só então concluir a validação.

---

## 9. Matriz de evidências obrigatórias

Para cada requisito, manter:
- ID único do requisito.
- Arquivo(s) alterado(s).
- Commit que contém a mudança.
- Teste automatizado correspondente.
- Resultado do teste e link da execução CI.
- Evidência manual, quando exigida.
- Estado: aprovado, bloqueado ou pendente.
- Risco residual conhecido.
- Observação de compatibilidade/migração.

Nenhum requisito será marcado como aprovado apenas porque o código compila. Build verde é necessário, mas não suficiente.

---

## 10. Critérios finais de aceite da STACY 4.5

A versão só pode ser considerada pronta quando todos os itens abaixo forem verdadeiros:

- [ ] Tempo ponta a ponta de conversa comum medido; P95 de até 10 s em condições controladas saudáveis.
- [ ] Deadline absoluto impede espera local indefinida e cobre a fila e retries.
- [ ] Pesquisa web tem perfil, estado e orçamento próprios.
- [ ] Retry não repete erros determinísticos nem excede deadline.
- [ ] Não há respostas duplicadas, tardias ou atribuídas à conversa errada.
- [ ] Estados de processamento sempre terminam em sucesso, erro ou cancelamento visível.
- [ ] Conexão API só é declarada depois de teste remoto válido.
- [ ] Teste API não contamina histórico nem contexto Gemini de sessão.
- [ ] Chave permanece protegida e nunca aparece em logs/histórico.
- [ ] Histórico persiste após fechamento, reinício e recriação de Activity.
- [ ] Cada sessão possui contexto Gemini próprio.
- [ ] Migração da 0.4.4 preserva tarefas, memórias e configurações.
- [ ] Conversa antiga não é inventada quando não existe dado local recuperável.
- [ ] Abrir, retomar, excluir individualmente e limpar tudo funcionam corretamente.
- [ ] Exclusão não afeta outras sessões nem dados fora do histórico.
- [ ] Gesto lateral executa retorno hierárquico sem encerrar o app em páginas internas.
- [ ] Gesto inferior Home/Recentes continua sob controle do Android.
- [ ] TalkBack, foco, contraste e escala de fonte não apresentam regressões críticas.
- [ ] Interface, orbe, animações, voz, tarefas, memória, pesquisa e ARS permanecem funcionais.
- [ ] CI, testes unitários, instrumentados e regressão aprovados.
- [ ] Upgrade real sobre 0.4.4 e instalação limpa aprovados.
- [ ] Release assinado, versionado e hash conferido.
- [ ] APK publicado no ARS corresponde exatamente ao artefato validado.
- [ ] Teste final no aparelho físico concluído.

---

## 11. Riscos residuais e limites que devem ser comunicados

- A meta de 10 segundos é uma meta de desempenho em condições normais, não uma promessa de que qualquer pergunta, pesquisa ou falha externa será resolvida nesse prazo.
- Google/Gemini, operadora, Wi-Fi, latência regional, limites de uso e disponibilidade externa não estão sob controle do aplicativo.
- Encerrar a espera no cliente não garante que o servidor remoto tenha interrompido o processamento.
- O histórico local só pode preservar mensagens a partir da implementação; mensagens antigas que nunca foram armazenadas localmente não podem ser reconstruídas com fidelidade.
- Excluir histórico local não garante exclusão de dados já retidos pelo provedor remoto.
- Testes em emulador não substituem testes de gesto em aparelho físico.
- Testes automatizados não substituem validação manual de experiência, legibilidade e comportamento visual.
- Nenhum pacote complexo pode ser declarado “sem falhas” antes de passar por todos os gates; falhas encontradas devem ser registradas e corrigidas, não ocultadas.

**Estado deste documento:** especificação e matriz detalhada registradas na branch.  
**Estado da implementação funcional:** pendente de execução e validação por frente.  
**Próxima ação:** executar Gate 0, registrar o baseline da 0.4.4 e iniciar Gate 1 (Gemini/CORE), sem publicar APK intermediário.
