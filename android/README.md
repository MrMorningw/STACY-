# Interface Android da STACY

A interface Android é a nova camada visual da STACY. Ela conversa com o
**STACY CORE** existente através do bridge HTTP local no Termux.

## Fluxo

Android → `127.0.0.1:8765` → `stacy_bridge.py` → `StacyOrchestrator` → resposta.

O bridge escuta somente em `127.0.0.1`; ele não é publicado na rede.

## Voz

A entrada e a saída de voz da interface usam as APIs nativas do Android:

- `SpeechRecognizer` para fala → texto;
- `TextToSpeech` para texto → fala;
- a permissão `RECORD_AUDIO` é solicitada somente quando o microfone é usado.

Os arquivos `AndroidVoice.kt` e `MainActivity.kt` formam essa camada. Se o
reconhecimento de voz ou o sintetizador não estiver disponível no aparelho,
a interface mantém o modo texto e apresenta o erro ao usuário.

## Anexos

O botão `+` abre o seletor de documentos do Android e permite selecionar
arquivos. Nesta etapa, a seleção é registrada na conversa; o envio do
conteúdo binário ao CORE será uma etapa posterior de integração multimodal.

## Toolchain

A configuração atual usa:

- Android Gradle Plugin 9.4.0;
- Gradle 9.6.0 ou superior;
- JDK 17;
- compileSdk 37;
- Kotlin/Compose Compiler 2.4.10;
- Compose BOM 2026.09.00.

## Execução

Na pasta `android`, com Android SDK e Gradle disponíveis:

```bash
gradle :app:assembleDebug
```

Depois, instale o APK de `app/build/outputs/apk/debug/app-debug.apk`.

Antes de abrir o aplicativo, no Termux, execute o bridge:

```bash
cd ~/stacy
python stacy_bridge.py
```

O teste mínimo é:

1. abrir STACY;
2. verificar `ONLINE`;
3. enviar `oi stacy`;
4. receber `Olá, senhor. Estou pronta.`;
5. tocar no microfone e repetir o teste por voz.

O APK e o bridge só devem ser considerados validados depois desse teste real
no aparelho.
