# Deployment Instructions

## Commits pendentes de deploy

- `34cd918`: fix - Add category information to SMS and WhatsApp messages
- `2c62512` e posteriores: version bumps

## Status

✅ Commits foram pushed para `192.168.178.47:/opt/kfz-kontakt.git`
❌ Post-receive hook tem erro: `not a git repository`
❌ SSH com password não está funcionando para deploy automático

## Como fazer deploy manualmente

Execute NO SERVIDOR (via SSH):

```bash
cd /opt/kfz-kontakt
git pull origin main
sudo systemctl restart kfz-kontakt
```

Ou, diretamente pelo server onde Python está rodando:

```bash
cd /opt/kfz-kontakt
git log --oneline -1  # Verificar o commit atual
```

Se o commit HEAD for `34cd918` ou posterior, o código já está atualizado.

## O que foi alterado

### `/backend/routes/scanner.py`

- **send_sms_contact()**: Agora inclui categoria na mensagem SMS
- **send_whatsapp_contact()**: Agora inclui categoria na mensagem WhatsApp

Exemplo:
```
KFZ Kontakt: [Schaden] Ich habe dir eine Nachricht...
```

Antes:
```
KFZ Kontakt: Ich habe dir eine Nachricht...
```

## Verificação

Depois do deploy:
1. Acessar QR-Code da aplicação
2. Preencher formulário com mensagem + categoria
3. Verificar no Twilio que a SMS/WhatsApp inclui `[categoria]`
