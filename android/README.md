# Interface Android da STACY

A camada Android é opcional e não altera o STACY CORE.

## Voz

A interface usa os comandos do Termux:API:

- `termux-speech-to-text` para entrada.
- `termux-tts-speak` para saída.
- `termux-notification` para notificações.

Se algum recurso não estiver instalado, a STACY informa a indisponibilidade e preserva o modo texto.

## Atalho Termux:Widget

O arquivo `stacy-voz.sh` pode ser colocado no diretório de scripts do Termux:Widget e tornado executável:

```bash
chmod +x stacy-voz.sh
```

O atalho chama `python stacy.py --voz` e, portanto, continua usando exatamente o mesmo CORE.

A instalação do aplicativo Termux:API e do plugin Termux:Widget é externa ao repositório; a ausência deles não impede o funcionamento textual da STACY.
