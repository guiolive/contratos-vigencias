# Controle de Vigências Contratuais — DLOG/PROAD/UFG

Painel público de acompanhamento das vigências dos contratos da UFG
(órgão 26235 / UG 153052), alimentado diariamente pela API de Dados
Abertos do Compras.gov.br.

## Estrutura

| Arquivo | Função |
|---|---|
| `index.html` | Painel (filtros, ordenação, exportação CSV) — carrega `dados.json` |
| `dados.json` | Base de contratos (24 meses de vigências) + data da posição |
| `atualizar.py` | Baixa os dados da API e regrava `dados.json` |
| `.github/workflows/atualizar.yml` | Roda `atualizar.py` às 6h (Brasília), dias úteis, e commita se houver mudança |

## Publicar no GitHub Pages

1. Criar repositório (ex.: `dlog-ufg/contratos-vigencias`) e enviar estes arquivos.
2. Settings → Pages → Source: **Deploy from a branch** → branch `main`, pasta `/ (root)`.
3. Settings → Actions → General → Workflow permissions: **Read and write permissions**
   (necessário para o bot commitar o `dados.json` atualizado).
4. Aba Actions → workflow "Atualizar dados dos contratos" → **Run workflow**
   (primeira carga manual, para validar).
5. Painel disponível em `https://<usuario>.github.io/<repo>/`.

## Publicar no domínio da DLOG

Mesmo repositório: Settings → Pages → Custom domain → informar o subdomínio
(ex.: `contratos.dlog.ufg.br`) e criar no DNS da UFG um registro CNAME
apontando para `<usuario>.github.io`. O GitHub emite o certificado HTTPS
automaticamente. Alternativa sem GitHub: copiar `index.html` + `dados.json`
para o servidor da DLOG e agendar `atualizar.py` num cron do servidor.

## Prompt sugerido para o Claude Code

> Neste diretório está um site estático (index.html + dados.json) com um
> workflow de atualização diária. Crie um repositório público chamado
> contratos-vigencias na minha conta, faça o commit inicial destes arquivos,
> ative o GitHub Pages na branch main (root), configure Workflow permissions
> como read-write e dispare o workflow "Atualizar dados dos contratos" para
> validar a primeira execução. Ao final, me dê a URL publicada.

## Observações

- A API é pública e sem autenticação; nenhum segredo é necessário no repositório.
- `dados.json` contém apenas dados públicos já disponíveis no Portal de Compras.
- O horário do cron usa UTC (9h UTC = 6h Brasília).
