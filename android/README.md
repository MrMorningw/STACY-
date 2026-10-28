# STACY para Android

## Núcleo nativo Kotlin

A rota de mensagens do APK funciona sem Termux, daemon Python ou servidor em localhost. O Kotlin faz o roteamento, responde a saudações e diagnósticos localmente, executa uma lista controlada de ações Android e salva tarefas e anotações explícitas em SQLite no próprio aparelho.

Conversas generativas e pesquisa na web usam a API Gemini Interactions diretamente por HTTPS.

### Primeira configuração da IA

1. Abra o menu lateral → **Configurações**.
2. Em **IA generativa**, selecione **Conectar**.
3. Crie uma chave em https://aistudio.google.com/apikey, cole-a e selecione **Salvar e testar**.
4. A STACY testa a API no chat. A chave é criptografada com AES-GCM usando uma chave gerenciada pelo Android Keystore; não é guardada no código, URL, logs ou repositório.

As mensagens enviadas à IA são processadas pelo Google. A STACY usa \`previous_interaction_id\` para manter o contexto, o que significa que o serviço guarda as interações de acordo com sua política de retenção e a modalidade da conta (a documentação atual descreve retenção padrão de 55 dias no nível pago e 1 dia no nível sem custo). Não envie senhas ou conteúdo que não queira processar em serviço externo. A API exige internet, chave válida e está sujeita à quota/condições da conta.

Sem chave ou internet, as funções locais continuam disponíveis e retornam diagnóstico explícito. O núcleo não fica esperando o Termux.

## Funções locais

- Saudações e verificação básica do CORE.
- Criar, listar e concluir tarefas no banco SQLite privado da STACY.
- Guardar e consultar anotações que o usuário pedir explicitamente para memorizar.
- Abrir aplicativos de uma lista permitida, abrir configurações/calendário, selecionar arquivos pelo seletor do Android e abrir o menu de compartilhamento.
- As ações permitidas são verificadas no lado Android. Uma resposta textual da IA não é considerada execução de ação.

## Build e validação

Na pasta \`android\`:

\`\`\`bash
gradle assembleDebug testDebugUnitTest
\`\`\`

O CI valida a rota nativa, compila o APK e executa testes unitários e de regressão. A validação em CI não substitui teste físico do APK com uma chave Gemini válida; esse teste de ponta a ponta precisa ser concluído no Android antes de declarar liberação final.

## ARS — autoconsulta e atualização

Abra **Configurações → ARS — Autoconsulta e atualização**. Ao entrar, a STACY consulta a versão instalada e o canal oficial. A consulta distingue versão atual, atualização disponível, canal atrasado, metadados inconsistentes e erro de rede.

Ao selecionar **Verificar e atualizar**, a ARS valida o caminho do APK, packageName, versão, SHA-256 e certificado antes de abrir o instalador Android. A instalação só é considerada concluída depois que o app retorna e o PackageManager confirma a versão-alvo. O Android pode exigir confirmação do usuário; a ARS não contorna essa proteção.

O mecanismo atualiza a aplicação e os módulos distribuídos dentro do APK. Não executa scripts ou código arbitrário baixado e não requer Termux.

Para validar localmente, use `gradle assembleDebug testDebugUnitTest assembleDebugAndroidTest`. O CI também executa os testes instrumentados no emulador; essa execução precisa terminar com sucesso para concluir a validação da ponte e da página ARS.

## Independência de runtime

O APK não contém inicializador de daemon Python, widget de shell, integração por comando ou dependência do Termux. O fluxo ativo é HTML/WebView → ponte Kotlin → CORE Kotlin/Android → Gemini por HTTPS. Voz, persistência local e automação do dispositivo são providas por APIs nativas do Android.

Os módulos Python restantes formam um runtime separado (CLI e servidor local opcional), independente de plataforma. Eles não são chamados pelo APK e não são necessários para instalar, iniciar, diagnosticar ou usar a STACY Android.
