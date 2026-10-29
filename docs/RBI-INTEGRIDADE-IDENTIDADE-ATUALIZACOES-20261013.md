# RBI — Integridade de identidade, núcleo e atualizações da STACY

Data de revisão: 2026-10-28  
Versão preparada nesta branch: 0.3.8 (versionCode 29)  
Estado: implementação em PR; validação em emulador e validação física ainda pendentes.

## Objetivo

Fazer a interface representar o estado real do aplicativo, separar falhas do núcleo de falhas da IA e permitir que a própria STACY consulte sua versão e conduza atualizações seguras, sem dependência operacional do Termux.

## Identidade de componentes

- Interface: HTML/WebView, incluindo o painel de diagnóstico do núcleo e a página ARS.
- Ponte: JavaScript chama métodos nomeados da interface Kotlin via WebView.
- CORE do APK: Kotlin/Android; comandos locais e persistência operacional usam SQLite.
- IA generativa: cliente Gemini por HTTPS; depende de internet, chave válida e quota.
- ARS: coordena autoconsulta, comparação com o canal oficial e atualização do APK. O manifesto é consultado em HTTPS; download, packageName, versionCode/versionName, SHA-256 e certificado são verificados.
- Termux/Python: não participa do fluxo de mensagens do APK. Os módulos Python restantes são um runtime independente e opcional, sem broadcasts de estado para o Android.
- Atualização pessoal/RIC e atualização do APK são responsabilidades separadas. A ARS não executa scripts arbitrários nem altera código ativo fora do ciclo validado de distribuição do APK.

## Regras de verdade do atualizador

1. O manifesto precisa conter versionCode positivo, versionName, packageName esperado, versão mínima do Android, SHA-256 e certificado de assinatura.
2. O versionCode declarado no ativo precisa corresponder ao manifesto; o nome do ativo e o versionName dentro do APK precisam corresponder à versão publicada.
3. O digest de topo e o digest do ativo precisam coincidir, e o arquivo baixado é verificado novamente.
4. A URL do APK precisa apontar para o caminho versionado do repositório oficial de atualização.
5. O APK baixado precisa ter packageName, versão, SHA-256 e certificado de assinatura esperados.
6. “Atualizada” só pode ser informado quando versionCode e versionName instalados coincidirem com o canal consultado.
7. Se o canal estiver atrás da versão instalada, for inconsistente ou falhar por rede, a ARS informa esse estado — nunca “já está atualizada”.
8. “Instalador aberto” não significa “instalação concluída”. A ARS guarda o alvo e só confirma após o Android informar que o código e nome esperados estão instalados.
9. A confirmação final da instalação é do Android; o aplicativo não tenta contornar as restrições da plataforma.

## Diagnóstico por camadas

O painel de Núcleo STACY deve reportar separadamente:

- HTML/JavaScript.
- Ponte WebView ↔ Kotlin.
- CORE Kotlin/Android.
- SQLite.
- Gemini/API generativa.
- Termux: NÃO UTILIZADO no fluxo do APK.
- Versão instalada e horário/latência dos testes.

Um resultado positivo do CORE local não deve mascarar uma falha Gemini. Uma falha Gemini não prova que o CORE local falhou.

## Validação obrigatória

- Testes unitários da política ARS (versões, canal atrasado, versão inconsistente e origem aprovada).
- Build Android, testes unitários e compilação do pacote instrumentado.
- Testes instrumentados em emulador: ponte WebView, diagnóstico por camada e controles ARS.
- Consultar o manifesto público após a publicação real; um build de PR não atualiza o canal oficial.
- Testar instalação de uma versão anterior para a nova, preservação de dados, cancelamento e confirmação após retorno do instalador.
- Fazer teste físico com o APK no dispositivo-alvo.
- Se a validação física ainda não ocorreu, registrar explicitamente “não validado em dispositivo”.

## Resultado desta revisão

Foi encontrado que o último teste instrumentado foi **cancelado pelo limite de 20 minutos do job**, após o emulador demorar aproximadamente 15 minutos a inicializar. Não foi uma falha de asserção concluída. O workflow foi ajustado para um runner mais estável, timeout de job maior, limite separado para testes instrumentados e recolha de resultados para diagnóstico.

A branch adiciona a página ARS, uma política determinística de comparação de versões, consulta do canal sem instalar, atualização verificada e confirmação da instalação após o retorno do Android. A integração final aguarda os testes instrumentados concluírem; a publicação do APK requer integração na main e secrets válidos do release.
