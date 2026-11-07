# STACY 0.4.5 — auditoria e plano de implementação

**Base auditada:** `main` em `7e93ab2d09fba1926c49aa91dc835ed9ec3b5e03` (2026-11-03)  
**Branch de trabalho:** `work/stacy-0.4.5-package-implementation`  
**Regra de release:** não publicar APK/release até concluir testes automatizados, regressão e validação em aparelho Android.

## Escopo aprovado

1. Desempenho e comunicação com Gemini.
2. Identificação real do estado da chave/conexão API.
3. Histórico permanente de conversas.
4. Gerenciamento e exclusão de conversas.
5. Navegação Android por gestos e retorno hierárquico.
6. Testes, integração e validação final.

Preservar a interface aprovada, identidade visual preta/laranja, orbe, animações e funções existentes.

## Achados confirmados na base

### Gemini e CORE
- `StacyAiClient` usa executor de thread única; uma chamada lenta pode manter solicitações seguintes na fila.
- Configuração atual: `thinking_level=medium`, `max_output_tokens=32768`, conexão 10 s, leitura 45 s para chat e 60 s para pesquisa, até quatro tentativas HTTP.
- Não há orçamento global de 10 s que cubra fila, conexão, geração e entrega. Os timeouts atuais permitem respostas muito acima da meta.
- A interface HTML usa watchdog de 70 s, coerente com os timeouts atuais, mas incompatível com a meta de UX abaixo de 10 s.
- O status de retry exibe `attempt/3`, enquanto o cliente permite quatro tentativas totais.
- A chave é armazenada de forma segura e existe fluxo de “Salvar e testar”; é necessário conferir o retorno completo desse teste e evitar tratar armazenamento como prova de conectividade.

### Histórico e conversas
- `StacyViewModel` mantém mensagens apenas em estado de memória; não há persistência de conversas nesse fluxo.
- `StacyLocalStore` persiste tarefas e memórias, mas não possui tabelas de conversas/mensagens.
- A seção “Conversas” da interface é atualmente uma tela de orientação/placeholder; não lista sessões reais nem abre conversas salvas.
- É necessário identificar um único repositório de histórico integrado ao fluxo real WebView/CORE, evitando criar dois históricos divergentes.

### Navegação Android
- `MainActivity` não apresenta tratamento explícito de retorno/back no código auditado.
- A interface possui navegação interna por seções e menu lateral, mas não foi encontrado um contrato claro de retorno coordenado entre drawer, páginas internas e back nativo.
- Implementar retorno com APIs Android atuais, respeitando a hierarquia interna e sem interceptar o gesto inferior de Home/Recentes.

### Testes e CI
- Há testes unitários e instrumentados para transporte Gemini e ponte WebView.
- O último commit da `main` é a versão 0.4.4, `versionCode=34`.
- O workflow de CI associado ao commit atual concluiu com sucesso em 2026-11-03. Isso não valida as mudanças da 4.5 nem substitui teste no aparelho.
- O workflow Android contém verificações de contrato, sintaxe JavaScript, build, testes e emulador; precisa ser executado novamente após as mudanças.

## Plano de implementação

1. **Estabilizar transporte:** separar perfil rápido de conversa e perfil de pesquisa; introduzir limite total por solicitação, cancelamento/expiração de fila, política de retry compatível com o orçamento e telemetria de duração por etapa. Não truncar respostas arbitrariamente nem inventar conteúdo para cumprir meta.
2. **Conexão API:** modelar estados desconectado/verificando/conectado/erro; só marcar conectado após resposta válida do teste; invalidar estado ao trocar/apagar chave e após falha relevante.
3. **Persistência:** adicionar schema versionado para sessões e mensagens, migrações não destrutivas, IDs estáveis, timestamps e operações transacionais; conectar o histórico ao fluxo de mensagens realmente exibido pela WebView.
4. **Gerenciamento:** listar/abrir sessões, excluir uma sessão, limpar todas com confirmação e atualizar a UI após sucesso do banco.
5. **Back Android:** coordenar drawer aberto, rota interna e back nativo; testar gesto lateral, botão back e navegação inferior do sistema em API compatível.
6. **Validação:** testes de banco/migração, transporte/timeout/retry, chave/API, navegação e WebView; build debug, unit tests, instrumented tests em emulador e regressão no aparelho físico.

## Critérios de aceite

- Conversa comum com meta de resposta inferior a 10 s em condições normais, com tempos medidos e falhas externas explicitadas.
- Pesquisa web com orçamento e estado de processamento próprios.
- Estado “conectado” somente após teste real bem-sucedido.
- Conversas recuperadas após encerramento/reabertura do app.
- Exclusão individual não afeta outras sessões; limpeza total exige confirmação.
- Gesto lateral retorna à página anterior; não encerra o app indevidamente; Home/Recentes continuam sob controle do Android.
- Nenhuma regressão visual ou funcional nos recursos já aprovados.
- APK 4.5 só após CI verde e validação em aparelho.

## Riscos e decisões técnicas obrigatórias

- A meta de 10 s não pode ser garantida quando rede/Gemini estiverem indisponíveis; o sistema deve encerrar a espera dentro do orçamento e informar o estado real.
- Alterações de persistência exigem migração explícita e preservação de dados existentes.
- O fluxo HTML/WebView é o caminho de conversa em uso; integrar a persistência nele e no CORE, sem duplicar o estado Compose.
- Não alterar a identidade visual para resolver problemas de navegação ou histórico.
