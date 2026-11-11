# Payment Provider: PaySuite

Módulo de pagamento para **Odoo 20** que integra o [PaySuite](https://paysuite.tech) (Moçambique), permitindo receber pagamentos por **M-Pesa, e-Mola, mKesh e cartão** no checkout do Odoo (eCommerce, facturas, links de pagamento).

- **Nome técnico:** `payment_paysuite`
- **Versão:** 20.0.1.0.0
- **Dependências:** `payment`
- **Moeda suportada:** MZN
- **Licença:** LGPL-3
- **Autor:** Hypertech, LDA

## Funcionalidades

- Redirecção do cliente para o checkout do PaySuite e regresso ao Odoo no fim do pagamento.
- Confirmação do estado real do pagamento através da API (`GET /payments/{id}`), sem confiar apenas nos dados recebidos.
- Webhook com validação da assinatura `X-Signature` (HMAC-SHA256 do corpo bruto com o webhook secret).
- Gestão automática de contactos: o módulo procura o cliente no PaySuite pelo email; se não existir, cria o contacto (nome, email e telefone) e associa-o ao pagamento.
- Telefone normalizado para E.164 (assume `+258` quando não há prefixo).
- Referência do pagamento limpa para aceitar apenas letras e dígitos, como exige o PaySuite.
- Se a criação do contacto falhar, o pagamento continua sem bloquear o cliente.

## Requisitos

- Odoo 20 (Community ou Enterprise) on-premise, Docker ou Odoo.sh. Não funciona no Odoo Online (SaaS), que não aceita módulos personalizados.
- Conta **de empresa** no PaySuite. As contas pessoais não têm acesso à API.
- Um URL público (HTTPS) para o Odoo, para que o PaySuite consiga chamar o webhook.

## Instalação

1. Copia a pasta `payment_paysuite` para a pasta de addons do Odoo (em Docker, a pasta montada em `/mnt/extra-addons`). O nome da pasta tem de ser exactamente `payment_paysuite`.
2. Reinicia o Odoo.
3. Activa o modo developer e vai a **Apps > Update Apps List**.
4. Remove o filtro "Apps" na pesquisa, procura **PaySuite** e clica em **Install**.

Alternativamente, instala por linha de comandos:

```bash
odoo -d NOME_DA_BASE -i payment_paysuite --stop-after-init
```

## Configuração

1. No painel do PaySuite, em **Settings > API Access**, gera o **API Token**.
2. No Odoo, vai a **Accounting > Configuration > Payment Providers > PaySuite**.
3. Preenche:
   - **API Token**: o token do passo 1.
   - **Webhook Secret**: o segredo usado para assinar os webhooks.
4. Define o estado como **Enabled** (ou **Test Mode** para testes).

Em **Settings > Technical > System Parameters**, confirma que `web.base.url` é o domínio público do teu Odoo. É a partir dele que o módulo constrói os URLs enviados ao PaySuite.

## Como funciona

1. O cliente escolhe PaySuite no checkout.
2. O Odoo procura (ou cria) o contacto no PaySuite e faz `POST /payments` com o `contact_id`, o `return_url` e o `webhook_url`.
3. O cliente paga no checkout do PaySuite.
4. O PaySuite redirecciona o cliente para o Odoo e envia o webhook. O Odoo valida a assinatura, consulta o pagamento na API e actualiza a transacção.

Rotas expostas pelo módulo (no teu Odoo):

| Rota | Método | Função |
|------|--------|--------|
| `/payment/paysuite/return` | GET, POST | Regresso do cliente após o checkout |
| `/payment/paysuite/webhook` | POST | Notificações do PaySuite |

Estas rotas são locais ao teu Odoo. Não são URLs do PaySuite.

## Desenvolvimento e testes

O PaySuite precisa de alcançar o teu Odoo, por isso `localhost` não serve para testar o webhook. Com o ngrok:

```bash
ngrok http 8069
```

1. Copia o URL `https://xxxx.ngrok-free.app`.
2. Em **System Parameters**, define `web.base.url` com esse URL e cria `web.base.url.freeze = True`.
3. Abre o Odoo por esse URL e faz o pagamento de teste.
4. Se necessário, define `proxy_mode = True` no `odoo.conf`.

Os pedidos recebidos ficam visíveis em `http://127.0.0.1:4040`.

## Resolução de problemas

| Problema | Causa provável |
|----------|----------------|
| `The Return URL field must be a valid URL` | `web.base.url` está como `localhost`. Usa um domínio público ou túnel. |
| O pagamento fica pendente e o webhook não chega | O PaySuite não consegue aceder ao teu Odoo. Verifica o URL público e o `web.base.url`. |
| Webhook devolve 403 | O Webhook Secret no Odoo não coincide com o do PaySuite. |
| O contacto não é criado | Consulta os logs por `PaySuite contact lookup/creation failed`. O pagamento segue na mesma. |
| 500 em todas as páginas após instalar | Erro de sintaxe ou de rota no módulo. Vê `docker compose logs --tail=80 odoo`. |

## Estrutura

```
payment_paysuite/
├── __init__.py
├── __manifest__.py
├── const.py
├── controllers/
│   └── main.py
├── models/
│   ├── payment_provider.py
│   └── payment_transaction.py
├── views/
│   └── payment_provider_views.xml
└── data/
    ├── payment_provider_data.xml
    └── payment_method_data.xml
```

## Suporte

Documentação da API: https://paysuite.tech/docs

Reporta problemas ou sugestões abrindo uma issue no repositório do módulo.