# RBI — Conexão da Interface, Acessibilidade e Recuperação do CORE

**Data:** 13/10/2026  
**Projeto:** STACY  
**Branch:** `stacy-ui-actions-accessibility-20261013`  
**PR:** #27 — Connect STACY quick actions and accessibility  
**Objetivo:** transformar os controles visíveis em ações utilizáveis, reforçar acessibilidade e evitar que uma chamada ao CORE deixe a fila travada indefinidamente.

## 1. Implementado nesta etapa

- Botão **+** abre um menu de ações rápidas conectado a consultas do CORE, calendário do Android, configurações do Android e compartilhamento da última resposta.
- Ponte JavaScript/Android expõe métodos nativos explícitos para abrir calendário, abrir configurações gerais e compartilhar texto.
- Campo de mensagem com rótulo acessível, envio por Enter, nomes explícitos nos botões, áreas de toque de 44 px, foco visível e anúncios de estado/resposta.
- Menu rápido com navegação por teclado (setas e Escape), gestão de foco e fechamento ao selecionar uma ação.
- Painéis ocultos marcados como inertes para impedir foco acidental; suporte a preferência de movimento reduzido.
- Controle de animações agora pausa e retoma o ciclo do orbe, em vez de apenas alterar um rótulo.
- Corrigido o fluxo de resposta: a resposta real do CORE não é substituída por texto demonstrativo e permanece visível depois que o estado volta para ONLINE.
- Adicionado timeout de 90 segundos na ponte do CORE; uma chamada travada retorna erro compreensível e libera a fila para solicitações seguintes.

## 2. Fluxo de integração

`Interface HTML → ponte Android (JavaScriptInterface) → StacyViewModel → StacyCoreBridge → Termux → CORE Python/ANPES → resultado → interface/voz`

A integração preserva o CORE existente. O APK ainda depende do Termux e do repositório STACY em `$HOME/stacy`; esta entrega não transforma o APK em pacote autossuficiente.

## 3. Segurança e limites

- As ações rápidas Android estão limitadas a operações explícitas já implementadas.
- A abertura de aplicativos permanece restrita à lista permitida existente.
- Nenhuma execução de shell arbitrário, autoedição de código ou autoalteração foi adicionada.
- Calendário e configurações são abertos com confirmação/controle normal do Android; compartilhamento abre o seletor do sistema.
- A consulta de tarefas, histórico, memória e estado do núcleo é enviada ao CORE; o comportamento final depende dos handlers já implementados no núcleo.

## 4. Validação e critérios de aceite

- [x] Revisão estática dos pontos de entrada e handlers da interface.
- [x] Conexão explícita dos controles de ações rápidas à ponte nativa.
- [x] Correção do ciclo de resposta demonstrativa e persistência do texto retornado.
- [x] Recuperação da fila por timeout do CORE.
- [ ] CI Android/build APK concluído para o último commit desta branch.
- [ ] Teste físico no aparelho: toque, teclado, leitor de tela, voz, atualização e retorno do Termux.
- [ ] Confirmar cada ação no aparelho com o CORE Python/ANPES instalado e funcional.

## 5. Estado

**Em validação de CI; teste físico pendente.** A interface está conectada ao CORE por meio do Termux, mas a autonomia plena e a execução autossuficiente dentro do APK não são declaradas concluídas. O próximo marco é validar o build e executar a matriz de testes no aparelho.
