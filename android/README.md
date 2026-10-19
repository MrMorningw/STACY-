# Interface Android da STACY

## Arquitetura atual do núcleo

A interface Android conversa com o STACY CORE Python por meio do serviço de comandos do Termux. **Nesta versão, o APK ainda não contém um runtime Python independente**: o Termux e o repositório do núcleo precisam estar instalados no aparelho.

## Preparação do CORE no Termux

1. Instale o Termux de uma fonte compatível e abra-o ao menos uma vez.
2. No Termux, habilite a opção que permite comandos de aplicativos externos. A STACY usa a permissão `com.termux.permission.RUN_COMMAND`.
3. Instale os requisitos básicos:

   ```bash
   pkg update
   pkg install python git
   ```

4. Disponibilize o repositório privado da STACY no caminho `$HOME/stacy` usando seu método autenticado de acesso ao GitHub. Não coloque token ou senha diretamente no código nem em comandos que fiquem salvos no histórico.
5. Nas versões recentes da STACY, o inicializador do CORE baixa os arquivos de runtime e tenta instalar automaticamente a dependência `requests` (primeiro pelo pacote do Termux e, se necessário, por `pip`). Se a instalação automática falhar, o log fica em `~/stacy/stacy-core-daemon.log`; tente no Termux:

   ```bash
   pkg install python-requests
   ```

   Para uma instalação manual do runtime, use:

   ```bash
   cd ~/stacy
   python -m pip install -r requirements.txt
   ```

6. Para habilitar os recursos que usam Gemini, crie `~/.stacy/secrets.json` no Termux com o conteúdo abaixo, substituindo o valor pela sua chave privada:

   ```json
   {"GEMINI_API_KEY":"SUA_CHAVE_PRIVADA"}
   ```

   Restrinja as permissões do arquivo e da pasta:

   ```bash
   chmod 700 ~/.stacy
   chmod 600 ~/.stacy/secrets.json
   ```

   A STACY também aceita a variável de ambiente `GEMINI_API_KEY`, que tem precedência sobre o arquivo. Nunca coloque a chave no repositório, no APK, em capturas de tela ou em mensagens.

7. Abra a STACY e envie uma mensagem simples. Se o núcleo ou uma dependência estiver ausente, a ponte Android deve devolver uma mensagem de diagnóstico.

A chave `GEMINI_API_KEY` é opcional para os fluxos locais; funcionalidades que dependem da API de IA precisam da chave configurada no ambiente do Termux. Nunca a publique no repositório.

## Voz e recursos opcionais

A interface usa comandos do Termux:API quando disponíveis:

- `termux-speech-to-text` para entrada de voz.
- `termux-tts-speak` para saída de voz.
- `termux-notification` para notificações.

A instalação do Termux:API e do plugin Termux:Widget é externa ao repositório. A ausência desses complementos não deve impedir o uso textual do CORE.

## Atalho Termux:Widget

O arquivo `stacy-voz.sh` pode ser colocado no diretório de scripts do Termux:Widget e tornado executável:

```bash
chmod +x stacy-voz.sh
```

O atalho chama `python stacy.py --voz` e continua usando o mesmo CORE.


## Ações nativas disponíveis nesta fase

O roteador Android aceita apenas comandos explícitos e uma lista permitida de ações. Exemplos de teste:

- `Abra as configurações do Android`
- `Abra o calendário`
- `Abra o WhatsApp`, `Abra o YouTube`, `Abra o Chrome`, `Abra o Gmail`, `Abra o Spotify` ou `Abra o Google Maps`
- `Selecione um arquivo`
- `Compartilhe: texto que você deseja compartilhar`

O compartilhamento apenas abre o seletor do Android; o usuário escolhe o aplicativo e confirma o envio. Aplicativos não instalados, ações desconhecidas e pacotes fora da lista são recusados. Nesta etapa, criar eventos de calendário, agendar notificações e executar comandos arbitrários não está conectado ao roteador conversacional.

## Validação obrigatória

O CI valida compilação e testes automatizados, mas não comprova a instalação do Termux, as permissões de execução externa, a presença de cada aplicativo ou a experiência de voz no aparelho. Esses itens devem ser registrados no RBI de validação física antes do fechamento do núcleo.
