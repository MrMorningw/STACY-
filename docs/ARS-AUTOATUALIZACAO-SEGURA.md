# ARS — Autoconsulta e atualização da STACY

## Finalidade

A ARS é o mecanismo que permite à própria STACY consultar seu estado, comparar a versão instalada com o canal oficial e conduzir uma atualização verificável. Não é apenas um relatório de auditoria e não é uma integração com o Termux.

## Fluxo de autoconsulta

1. Ler a versão instalada diretamente do Android PackageManager.
2. Consultar o manifesto público oficial update.json pelo canal HTTPS.
3. Validar identidade do pacote, versionCode/versionName, versão mínima do Android, consistência do SHA-256, certificado publicado e endereço do APK.
4. Classificar o resultado sem falsos positivos: atualizada, atualização disponível, canal atrasado, canal inconsistente ou consulta falha.
5. Mostrar a resposta na interface mesmo que o usuário navegue para outra seção durante a consulta.
6. Guardar o estado da última consulta na interface até uma nova consulta.

## Fluxo de atualização

1. A ARS só inicia o download de uma versão com versionCode superior à instalada.
2. O download só pode vir do caminho versionado do repositório oficial de atualizações.
3. Antes de abrir o instalador, conferir SHA-256, packageName, versionCode, versionName e certificado de assinatura.
4. O Android apresenta a confirmação de instalação. O app não contorna a política de instalação do sistema.
5. Quando o aplicativo retornar do instalador, comparar a versão real do PackageManager com o destino pendente. Só então informar “instalação confirmada”.
6. Se o usuário cancelar, o sistema não confirmar a versão ou a rede falhar, reportar que a atualização não foi concluída.

## Separação de responsabilidades

- A autoconsulta da ARS é nativa e não depende de Python, daemon local, RUN_COMMAND, broadcasts ou Termux.
- Atualizações de código e módulos incorporados ao APK são distribuídas como APK assinado pelo canal oficial.
- A ARS não baixa nem executa scripts arbitrários e não reescreve arquivos de código ativo em tempo de execução.
- A atualização do APK é distinta de atualizações de dados pessoais, memória, RIC e conteúdo operacional. Qualquer pacote de dados futuro precisará de manifesto versionado, esquema permitido, integridade validada e caminho de recuperação próprios.

## Estados obrigatórios

- up_to_date — versionCode e versionName instalados coincidem com o canal consultado.
- update_available — existe versão oficial mais nova.
- channel_outdated — o canal publica uma versão inferior à instalada; nunca dizer que está atualizada.
- channel_inconsistent — nomes, códigos ou metadados do canal não coincidem.
- error — rede, servidor ou metadados impediram a conclusão. Erro não equivale a “já está atualizada”.

## Critérios de validação

- Testes unitários da política de versão e da origem permitida do APK.
- Teste instrumentado da página ARS e da ponte WebView/Kotlin.
- Build, testes unitários e testes instrumentados Android aprovados.
- Teste de uma atualização real em dispositivo: instalação, preservação de dados, cancelamento e confirmação da versão após retorno.
- Registro explícito de qualquer parte que ainda não foi validada em dispositivo físico.
