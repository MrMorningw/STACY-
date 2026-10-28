# RBI — Referências, arquitetura e critérios de fechamento da STACY

**Finalidade:** transformar as inspirações do projeto em requisitos verificáveis, preservando a identidade STACY e evitando marcar como concluída uma capacidade que ainda não passou por teste integrado.

## 1. Referências e o que aproveitar

### JARVIS de Tony Stark — visão de produto
Adotar como norte: assistente conversacional com contexto, voz, estado operacional visível e ações executadas com segurança. Não tratar capacidades fictícias (consciência, percepção universal, autonomia ilimitada) como requisitos técnicos literais.

### J.A.R.V.I.S. de Lucas Victor
Referência pública: https://jarvis.lucasvictor.ai/

Princípios a avaliar: memória de longo prazo visível e controlável, contexto pessoal, voz, briefing, integrações, painéis reativos e confirmação de ações importantes. A página pública descreve uma experiência conectada a vários serviços; cada integração da STACY deve ser implementada e testada individualmente, nunca inferida a partir da aparência do painel.

### FatihMakes / MARK — referência técnica
Repositório de referência: https://github.com/FatihMakes/Mark-LV

O projeto demonstra uma organização modular para assistente de voz, ferramentas, configuração e interface. Aproveitar os princípios de modularidade, inicialização com diagnóstico, ferramentas declaradas e tratamento de dependências. Não transplantar código de desktop para Android sem avaliar compatibilidade, licenças e dependências; as bibliotecas de interface/controle de computador não são equivalentes às APIs Android.

### Inteligência Mil Grau
Canal: https://www.youtube.com/@inteligenciamilgrau

Usar como fonte de estudo para agentes, modelos, orquestração e aplicações de IA. Vídeos e demonstrações servem como pistas de pesquisa, não como prova de que um recurso esteja operacional no código da STACY.

### Identidade visual STACY
Preservar fundo preto, neon laranja, átomo/orbe com núcleo “S”, Space Stacked, constelações DR/LM e linguagem natural em português brasileiro. A interface deve refletir o estado real do sistema, não fingir que uma ferramenta está funcionando.

## 2. Matriz de comparação e decisão

| Área | Referência desejada | Situação observada no repositório | Critério para fechar |
|---|---|---|---|
| Núcleo/orquestração | Um caminho de decisão coerente | O CORE Python e o orquestrador existem | Testes de roteamento, regressão e resposta JSON no Android |
| Contexto da conversa | Continuidade entre turnos | O orquestrador mantém contexto em memória do processo; Android inicia um novo processo por mensagem | Persistir estado de sessão com validação, gravação atômica e bloqueio contra chamadas concorrentes |
| Memória pessoal | Persistente, visível e controlável | `memory.py` grava memória persistente; contexto conversacional é separado | Testar leitura, gravação, exclusão e isolamento de contexto no Android |
| Ferramentas | A IA propõe; o CORE valida; a ferramenta executa | Tarefas/memória existem; `AndroidAutomation.kt` contém ações nativas, mas a ligação ponta a ponta ainda precisa ser provada | Contrato de ferramenta tipado, validação de argumentos, confirmação quando necessária e teste do resultado real |
| Pesquisa | Fontes verificáveis e falha explícita | O caminho de pesquisa externa existe; a ponte Android agora encaminha até cinco fontes com URL HTTPS para a interface | Confirmar fontes reais e que falhas não sejam apresentadas como pesquisa concluída |
| Voz | Ouvir, entender, responder e refletir o estado real | Entrada/saída de voz existe no app; acionamento por palavra-chave/assistente padrão não está provado | Testes em dispositivo real, permissões, interrupção, fallback para texto e botão lateral |
| Interface reativa | Painéis e estados ligados ao sistema real | HUD WebView e páginas de navegação existem | Cada painel deve mostrar dados reais ou declarar claramente que ainda não está conectado |
| Ações Android | Abrir apps/configurações, calendário, notificações e compartilhamento | Há implementações nativas de ações, mas o despacho a partir do CORE precisa ser confirmado | Teste por ação, permissões, cancelamento e retorno de sucesso/erro |
| Atualizações / ARS | Autoconsulta e atualização verificável da STACY | Página ARS, comparação de versão e validação de manifesto/APK estão implementadas na branch | Executar testes instrumentados, testar instalação real e confirmar versão após retorno do instalador |
| Privacidade | Segredos e memória fora do código versionado | Chave Gemini é gerida pelo Android Keystore; o APK não depende do Termux | Confirmar armazenamento/recuperação da chave no dispositivo e evitar segredos em logs/JSON |
| Identidade visual | Preto/laranja e UI em português | Protótipo implementado | Regressão visual sem alterar a identidade aprovada |

## 3. Contrato arquitetural obrigatório

Fluxo esperado:

`Interface Android → Ponte nativa → CORE Python → Orquestrador → Política de segurança → Ferramenta → Resultado estruturado → Interface/voz`

Regras:
1. A interface não executa comandos arbitrários do modelo.
2. O CORE escolhe entre responder, pesquisar ou propor uma ferramenta usando resultados estruturados.
3. A ferramenta valida parâmetros e permissões antes de executar.
4. Ações destrutivas, externas ou que afetem terceiros exigem confirmação explícita.
5. O retorno informa sucesso real ou falha; nunca declara sucesso antes da confirmação do sistema operacional.
6. Toda execução termina em um estado definido: ONLINE, OUVINDO, PENSANDO, PESQUISANDO, EXECUTANDO, RESPONDENDO, ERRO ou OFFLINE.
7. Dados temporários da conversa não devem ser confundidos com memória pessoal persistente.
8. O protocolo Android deve emitir uma única resposta JSON em stdout; diagnósticos vão para stderr.
9. O estado entre processos deve ser validado, limitado, protegido por permissões e gravado atomicamente.
10. A ARS consulta e atualiza o APK pelo canal assinado; Atualização Pessoal/RIC é fluxo separado. Nenhum dos fluxos pode executar scripts arbitrários ou marcar sucesso sem confirmação verificável.

## 4. Critérios de aceite do núcleo

- [ ] Testes Python, compilação Android e testes unitários aprovados no mesmo commit.
- [ ] Duas mensagens consecutivas mantêm o contexto esperado.
- [ ] Confirmação de ação pendente sobrevive ao próximo processo sem executar duas vezes.
- [ ] Mensagens simultâneas não corrompem nem sobrescrevem a sessão.
- [ ] Estado corrompido não reaproveita ação pendente; o sistema informa a recuperação.
- [ ] Ausência do Termux, Python, dependência ou chave externa gera diagnóstico honesto e modo local quando possível.
- [ ] Nenhuma chave secreta aparece no repositório, logs ou resposta JSON.
- [ ] Cada ferramenta Android é exercitada no aparelho e devolve o resultado real.
- [ ] Voz, botão lateral e seleção como assistente padrão são testados no dispositivo-alvo.
- [ ] A interface não apresenta conteúdo fictício como dado conectado.
- [ ] A ARS é testada do canal consultado até a abertura do instalador; o retorno do Android confirma a versão realmente instalada e a preservação de dados.
- [ ] RBI de fechamento registra commit, APK, resultados de CI, testes no dispositivo e limitações restantes.

## 5. Estado do trabalho nesta rodada

A branch de correção mantém o fluxo ativo do APK em HTML/WebView → ponte Kotlin → CORE Kotlin/Android → Gemini por HTTPS. A ARS foi adicionada como mecanismo nativo para consultar versão/canal, classificar canal atualizado/atrasado/inconsistente e conduzir atualização de APK validado.

O último teste instrumentado foi cancelado pelo limite de 20 minutos do job antes de produzir resultado; o log mostra que o emulador levou cerca de 15 minutos para inicializar. O workflow foi ajustado para dar tempo à inicialização e coletar os resultados dos testes. A compilação e a suíte Python passaram em execuções anteriores, mas a validação instrumentada no commit final ainda é necessária.

## 6. Limites arquiteturais e de liberação

O APK não usa Termux, Python ou daemon local no caminho de mensagens. A ARS não instala silenciosamente nem executa código arbitrário: verifica o canal oficial, valida o pacote e pede a confirmação final ao instalador Android. O canal público só será atualizado quando o PR for integrado à main e o workflow de release assinado executar com os secrets corretos. Teste físico, preservação de dados e instalação real continuam pendentes.
