# STACY 0.4.5 — status de implementação e publicação ARS

**Release alvo:** 0.4.5  
**versionCode:** 35  
**Pacote Android:** `com.mrmorning.stacy`  
**Base:** `main` em `7e93ab2d09fba1926c49aa91dc835ed9ec3b5e03`  
**Branch:** `work/stacy-0.4.5-package-implementation`

## Situação técnica

O pacote de implementação da 0.4.5 reúne as seis frentes previstas na auditoria:

1. Transporte Gemini/CORE com fila limitada, deadline, tentativas controladas e métricas de latência.
2. Teste remoto isolado da chave Gemini e estados explícitos de conexão.
3. Persistência SQLite de conversas, mensagens e contexto remoto individual por conversa.
4. Abertura, paginação, exclusão individual e limpeza do histórico local.
5. Navegação de retorno coordenada entre WebView e Android.
6. Testes unitários, instrumentados, de transporte, banco e ponte.

A versão do Gradle foi atualizada para `versionName=0.4.5` e `versionCode=35`. O incremento é necessário para o Android reconhecer a atualização sobre a 0.4.4 (code 34).

## Evidências de CI existentes antes do incremento de versão

As quatro execuções abaixo foram concluídas com sucesso no commit anterior `27982a2d95e0d149fe618c773ec7a57f3fc3803e`:

- [STACY Android CI](https://github.com/MrMorningw/STACY-/actions/runs/42333026786) — compilação debug, testes unitários, pacote de testes instrumentados e execução instrumentada em emulador concluídos.
- [STACY Core CI](https://github.com/MrMorningw/STACY-/actions/runs/42333026896) — regressão do CORE concluída.
- [STACY MP-10 CI](https://github.com/MrMorningw/STACY-/actions/runs/42333026784) — regressão MP-10 concluída.
- [STACY MP-11 CI](https://github.com/MrMorningw/STACY-/actions/runs/42333026837) — regressão MP-11 concluída.

Os artefatos daquele commit eram de depuração e foram gerados quando o Gradle ainda declarava 0.4.4 / code 34. Portanto, não são o pacote de instalação 0.4.5 e não devem ser distribuídos como tal.

**Gate após a alteração de versão:** repetir todas as execuções relevantes no novo SHA. Não reutilizar a evidência do commit anterior como se fosse evidência do commit atualizado.

## Caminho de publicação ARS

O workflow `.github/workflows/android-ci.yml` executa a publicação assinada somente depois de sucesso no push para `main`. O script `scripts/publish_stacy_update.sh`:

- monta o APK release;
- valida package name, versão, assinatura e certificado SHA-256 fixado;
- calcula o SHA-256 do APK;
- publica `releases/STACY-0.4.5.apk` e `update.json` no repositório ARS `MrMorningw/STACY---UPTADES-DEFINITIVO`.

O manifesto ARS atual observado antes desta versão ainda aponta para 0.4.4 / code 34. A publicação 0.4.5 só é considerada concluída depois de confirmar que o manifesto remoto foi atualizado para code 35, versão 0.4.5, hash do novo APK e link de download correspondente.

## Validação final no aparelho físico

A execução instrumentada em emulador não comprova comportamento em aparelho real. Após disponibilizar a build candidata no ARS, a validação física deve cobrir, no mínimo:

- instalar/atualizar sobre a 0.4.4 sem desinstalar;
- confirmar versão 0.4.5 e preservação de tarefas/memórias;
- testar a conexão Gemini e uma conversa comum;
- abrir, retomar, excluir uma conversa e limpar o histórico;
- reiniciar o aplicativo e confirmar persistência;
- navegar por páginas internas com gesto lateral e testar Home/Recentes;
- verificar voz, tarefas, memória, pesquisa, animações e atualizador.

A publicação solicitada para teste não equivale ao aceite final em aparelho físico. Falhas observadas nesse teste devem ser registradas e corrigidas antes de declarar a 0.4.5 definitivamente aprovada.

## Critério de conclusão

Marcar a 0.4.5 como publicada para teste somente quando:

- [ ] CI do SHA final estiver verde;
- [ ] build release tiver sido gerada e assinatura validada pelo pipeline;
- [ ] arquivo APK estiver no repositório ARS;
- [ ] `update.json` remoto apontar para 0.4.5 / code 35 e hash do APK publicado;
- [ ] link direto de download responder e baixar o artefato esperado.

Marcar como definitivamente aprovada somente depois da validação física descrita acima.
