# RBI — Conexão da Interface, Acessibilidade e Recuperação do CORE

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