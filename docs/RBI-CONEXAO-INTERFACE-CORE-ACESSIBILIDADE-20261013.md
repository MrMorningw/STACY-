# RBI — Conexão da Interface, Acessibilidade e Recuperação do CORE

> **Nota de estado (2026-10-28):** o fluxo Interface → Termux/Python descrito abaixo é histórico e retrata a implementação da data deste relatório. O APK atual usa HTML/WebView → ponte Kotlin → CORE Kotlin/Android → Gemini por HTTPS, sem Termux no caminho de mensagens. A ARS e a validação atual estão documentadas em `docs/ARS-AUTOATUALIZACAO-SEGURA.md`.



**Data:** 13/10/2026  
**Projeto:** STACY  
**Branch:** `stacy-ui-actions-accessibility-20261013`  
**PR:** [#27 — Connect STACY quick actions and accessibility](https://github.com/MrMorningw/STACY-/pull/27)  
**Commit em main:** `09b78a151a04cbaa141f99f977d68d04f46499ee`  
**Versão publicada:** `0.1.7` — `versionCode 8`  
**Objetivo:** transformar os controles visíveis em ações utilizáveis, reforçar acessibilidade e evitar que uma chamada ao CORE deixe a fila travada indefinidamente.

## 1. Implementado nesta etapa

- Botão **+** abre um menu de ações rápidas conectado a consultas do CORE, calendário do Android, configurações do Android e compartilhamento da última resposta.
- Ponte JavaScript/Android expõe métodos nativos explícitos para abrir calendário, abrir configurações gerais e compartilhar texto.
- Campo de mensagem com rótulo acessível, envio por Enter, nomes explícitos nos botões, áreas de toque de 44 px, foco visível e anúncios de estado/resposta.
- Menu rápido com navegação por teclado (setas e Escape), gestão de foco e fechamento ao selecionar uma ação.
- Painéis ocultos marcados como inertes para impedir foco acidental; suporte a preferência de movimento reduzido.
- Controle de animações pausa e retoma o ciclo do orbe.
- Corrigido o fluxo de resposta: a resposta real do CORE não é substituída por texto demonstrativo e permanece visível depois que o estado volta para ONLINE.
- Adicionado timeout de 90 segundos na ponte do CORE; uma chamada travada retorna erro compreensível e libera a fila para solicitações seguintes.

## 2. Fluxo de integração

`Interface HTML → ponte Android (JavaScriptInterface) → StacyViewModel → StacyCoreBridge → Termux → CORE Python/ANPES → resultado → interface/voz`

A integração preserva o CORE existente. O APK ainda depende do Termux e do repositório STACY em `$HOME/stacy`; esta entrega não transforma o APK em pacote autossuficiente.

## 3. Segurança e limites

- As ações rápidas Android estão limitadas a operações explícitas já implementadas.
- A abertura de aplicativos permanece restrita à lista permitida existente.
- Nenhuma execução de shell arbitrário, autoedição de código ou autoalteração foi adicionada.
- Calendário e configurações são abertos com os controles normais do Android; compartilhamento abre o seletor do sistema.
- A consulta de tarefas, histórico, memória e estado do núcleo é enviada ao CORE; o comportamento final depende dos handlers já implementados no núcleo.

## 4. Validação

- [x] Revisão estática dos pontos de entrada e handlers da interface.
- [x] Conexão explícita dos controles de ações rápidas à ponte nativa.
- [x] Correção do ciclo de resposta demonstrativa e persistência do texto retornado.
- [x] Recuperação da fila por timeout do CORE.
- [x] CI Android concluído com sucesso no commit de main.
- [x] `gradle assembleDebug testDebugUnitTest` concluído com sucesso.
- [x] Artefato APK de debug gerado no workflow.
- [x] Build release assinado e verificado por `apksigner` no workflow de publicação.
- [x] APK `STACY-0.1.7.apk` publicado no repositório oficial de atualizações.
- [x] `update.json` publicado com `versionCode 8`, SHA-256 e certificado de assinatura.
- [ ] Teste físico no aparelho: toque, teclado, leitor de tela, voz, atualização e retorno do Termux.
- [ ] Confirmar cada ação no aparelho com o CORE Python/ANPES instalado e funcional.

**Workflow CI/publicação:** [Execução #206 — sucesso](https://github.com/MrMorningw/STACY-/actions/runs/38349210704)  
**Canal oficial de atualização:** [update.json](https://github.com/MrMorningw/STACY---UPTADES-DEFINITIVO/blob/main/update.json)  
**APK publicado:** [STACY-0.1.7.apk](https://github.com/MrMorningw/STACY---UPTADES-DEFINITIVO/blob/main/releases/STACY-0.1.7.apk)  
**SHA-256 do APK assinado:** `298c4ef4a6342a9c882abb3e0f840eb3cb26316c1eb27502ba4097ef30185cf4`  
**Certificado SHA-256:** `6adc9b10b2e4c20f15985d315694063efed0cbe885d6cacf424248708980034b`

## 5. Estado atual e próximos passos

**Build, testes automatizados e publicação oficial concluídos. Teste físico ainda pendente.** A versão 0.1.7 já está disponível no canal interno de atualização. No aparelho, abrir STACY → Atualizações e solicitar nova verificação. Não é necessário desinstalar a versão anterior; preservar os dados e validar a atualização in-place.

Após atualizar, executar a matriz de testes no aparelho:
1. Abrir a STACY e verificar versão 0.1.7.
2. Testar envio de mensagem e resposta real do CORE.
3. Testar botão +, consulta do CORE/tarefas, calendário, configurações e compartilhamento.
4. Validar microfone/voz, navegação por teclado quando aplicável, leitor de tela e movimento reduzido.
5. Confirmar Termux e `$HOME/stacy` ativos, além do retorno de ANPES/CORE.
6. Provocar uma falha controlada de resposta e confirmar que o timeout libera a fila sem travar a interface.

**Limite importante:** a conexão com o CORE existe via Termux; a autonomia plena e a execução autossuficiente dentro do APK não estão declaradas concluídas.

## 6. Etapa de reorganização funcional — em desenvolvimento

- O botão **+** passa a oferecer câmera, fotos/imagens e arquivos, usando o seletor de arquivos do WebView/Android e exibindo os nomes selecionados.
- **Limite de anexos nesta etapa:** o CORE ainda recebe texto pela ponte atual; os bytes dos arquivos não são transmitidos ao núcleo. A interface informa isso para não sugerir análise de imagem/documento que ainda não existe.
- Adicionadas as seções laterais **Ferramentas** e **Permissões**. Ferramentas reúne calendário, configurações, compartilhamento e verificação do CORE; Permissões direciona ao painel real de permissões do Android.
- Próximo requisito técnico: implementar transporte de anexos seguro até o CORE e validar no dispositivo. Não declarar essa parte concluída antes do teste.


## 7. Correção prioritária do retorno do CORE — 13/10/2026

- **Causa provável do estado “pensando” sem resposta:** o `PendingIntent` entregue ao Termux estava marcado como `FLAG_IMMUTABLE`. O serviço do Termux precisa anexar o bundle de resultado ao callback; em Android moderno, a imutabilidade pode impedir a entrega dos dados de retorno, deixando a interface sem resposta até o timeout.
- **Correção:** o callback agora usa `FLAG_MUTABLE` a partir do Android 12 (API 31), mantendo `FLAG_ONE_SHOT` e `FLAG_UPDATE_CURRENT`. Em versões anteriores, usa apenas os flags compatíveis.
- **Próxima versão:** `0.1.9`, `versionCode 10`.
- **Validação obrigatória:** compilar, executar os testes e confirmar publicação assinada; depois testar no aparelho o ciclo comando → Termux/Python → broadcast com JSON → resposta na interface. A causa é tecnicamente plausível e a correção foi aplicada, mas o teste físico ainda é necessário para confirmar a causa no dispositivo.


## 8. Conversa visível, animação de resposta e menu rolável — 13/10/2026

- A interface mantém um registro visual de mensagens do usuário e respostas da STACY, incluindo estado transitório de processamento substituído pela resposta ou por mensagem de erro.
- O estado RESPONDENDO é mantido por 1,4 segundo antes de voltar a ONLINE, em vez de desaparecer imediatamente.
- A barra lateral passou a usar layout flexível com rolagem vertical real, barra de rolagem discreta e rodapé preservado, permitindo alcançar Configurações em telas pequenas.
- Versão alvo: 0.2.0 / versionCode 11.
- Validação em CI e teste físico são obrigatórios. A conversa visual depende de o CORE retornar texto válido; a interface não cria respostas fictícias quando o CORE falha.
