# RBI — Integridade de identidade, componentes e atualizações da STACY
Data: 2026-10-13
Versão alvo: 0.2.3 (versionCode 14)
Status: implementação proposta; validação automática pendente; validação física pendente.

## Objetivo
Impedir que a STACY declare “já está atualizada” quando o canal publicado estiver inconsistente, atrasado ou apontar para um pacote que não corresponde à versão anunciada. A identificação dos componentes deve descrever arquitetura real, não simular saúde operacional.

## Identidade interna dos componentes
- Interface Android/WebView: recebe comandos, apresenta estados e mensagens.
- Ponte Android/CORE: envia pedidos ao serviço de execução do Termux e aguarda callback.
- CORE Python via Termux: dependência externa atual para raciocínio e execução; não está incorporado integralmente ao APK.
- Canal de atualização: manifesto update.json, APK publicado, versionCode/versionName, packageName, SHA-256 e certificado de assinatura.
- MPEF Atualizações: fluxo separado de atualização pessoal via RIC e atualização do aplicativo/APK. Uma ação não deve ser apresentada como concluída sem confirmação verificável.

## Regras de verdade do atualizador
1. O manifesto deve conter versionCode positivo, versionName, packageName esperado, SHA-256 do APK e hash do certificado.
2. O version_code do ativo e o versionCode do manifesto devem coincidir.
3. O digest do ativo e o SHA-256 de topo do manifesto devem coincidir.
4. packageName deve ser com.mrmorning.stacy; o APK baixado precisa corresponder ao pacote, versão, digest e certificado publicados.
5. Só informar que a instalação corresponde à versão publicada quando versionCode e versionName instalados coincidirem com o canal consultado.
6. Se o canal estiver atrás da instalação, os metadados divergirem ou a verificação falhar, reportar inconsistência específica. Nunca transformar erro, timeout, ausência de rede ou metadados inválidos em “já está atualizada”.
7. “Pacote validado e instalador aberto” não significa “atualização instalada”. A instalação final depende da confirmação do Android e deve ser verificada ao reabrir o app.

## Estados que a interface deve diferenciar
- Verificando canal…
- Nova versão encontrada: instalada → publicada.
- Baixando e validando integridade…
- Pacote validado; aguardando confirmação do instalador Android.
- Verificação concluída: versão instalada corresponde à publicada; nenhuma versão mais nova anunciada.
- Falha de rede/servidor.
- Canal inconsistente/desatualizado.
- Integridade, pacote ou assinatura inválidos.
- Termux/CORE indisponível ou sem retorno (diagnóstico separado do estado do APK).

## Validação obrigatória
- CI/testes/compilação Android aprovados.
- Manifesto público conferido depois da publicação, não apenas depois da compilação.
- Instalação e atualização real testadas em Android.
- CORE validado com comando real no dispositivo: enviar → estados visuais → resposta do CORE na conversa.
- Se não houver teste físico, o RBI deve dizer explicitamente “não validado em dispositivo”.

## Limites
A compilação aprovada não comprova que o Termux, Python, dependências, credenciais ou CORE estejam instalados/configurados no telefone. O estado “ONLINE” da interface não deve ser usado como prova dessas dependências.
