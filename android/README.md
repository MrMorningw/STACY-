# STACY para Android

## Núcleo nativo

O APK usa Kotlin para comandos locais e chama a API Gemini Interactions diretamente por HTTPS para conversa generativa. O caminho principal do Android **não depende de Termux, Python, daemon local ou servidor em localhost**. A API oferece continuidade de conversa pelo `previous_interaction_id` e pesquisa web via Google Search. Os scripts Python/Termux que permanecem no repositório são legados/ferramentas de desenvolvimento, não requisitos para conversar pelo APK.

### Primeira configuração da IA

1. Abra a STACY e entre no menu lateral → **Ajustes**.
2. Crie uma chave da Gemini API em https://aistudio.google.com/apikey.
3. Cole a chave no diálogo e selecione **Salvar e testar**.
4. A STACY testa a conexão na hora e devolve o resultado no chat. A chave é cifrada com AES-GCM usando uma chave gerenciada pelo Android Keystore; ela não é gravada no código, URL, log ou repositório.

A API generativa precisa de internet e de uma chave válida; o uso pode estar sujeito à quota e às condições da conta Google. Para manter o contexto entre mensagens, a API Interactions mantém as interações no lado do serviço e a STACY guarda apenas o identificador da interação no armazenamento privado do app; a retenção depende da modalidade da conta e das configurações do Google. Não envie senhas ou conteúdo que não queira processar no serviço externo. Sem chave ou sem internet, os comandos locais continuam disponíveis e a STACY retorna um diagnóstico explícito em vez de ficar aguardando o Termux.

## Comandos nativos e recursos

A interface local mantém tarefas, objetivos, projetos, preferências, foco e memória no armazenamento local do WebView. A ponte Android também oferece ações permitidas como abrir configurações/calendário, abrir aplicativos autorizados e compartilhar texto. O sistema não afirma executar ações que não foram realizadas.

## Compilação e validação

Na pasta \`android\`:

\`\`\`bash
gradle assembleDebug testDebugUnitTest
\`\`\`

O CI executa validações estáticas, compilação e testes unitários, depois publica o APK de depuração como artefato do workflow. A validação automática não substitui um teste físico no dispositivo; a primeira configuração da IA deve terminar com a mensagem de conexão validada.

## Núcleo Python legado

O CORE Python continua no repositório para desenvolvimento e compatibilidade com os atalhos antigos do Termux. A interface Android nativa não o inicia nem usa o servidor local em sua rota de chat.
