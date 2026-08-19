# Painel de vigências contratuais — DLOG/PROAD/UFG

## O problema que este projeto resolve

Os gestores de contrato da UFG não avisam o departamento de compras com
antecedência quando um contrato precisa ser renovado — às vezes avisam com uma
semana. Renovação de contrato público passa por procuradoria e uma série de
trâmites que levam meses. Em julho/2026 o contrato do Google (Gmail
institucional) quase foi extinto porque a renovação não andou a tempo.

Este painel puxa os contratos ativos da UG 153052 da API do Comprasnet
Contratos e mostra quem vence em até 24 meses, classificado por urgência, com
o nome do gestor de cada contrato. O objetivo é o departamento de compras
enxergar o vencimento ANTES do gestor avisar, e cobrar com meses de
antecedência — do gestor certo.

## Arquitetura (como o dado chega no HTML)

1. `atualizar.py` roda todo dia útil às 6h (GitHub Actions,
   `.github/workflows/atualizar.yml`). Sem autenticação — endpoints públicos.
   Faz 1 + 633×2 chamadas (~25 min):
   - `GET /api/contrato/ug/153052` — lista completa de ativos da UG (1 chamada,
     ~2 min de resposta, sem paginação)
   - `GET /api/contrato/{id}/empenhos` — execução financeira, por contrato
   - `GET /api/contrato/{id}/responsaveis` — gestor e fiscais, por contrato
2. O script filtra, calcula e grava tudo em `dados.json` (~200 KB), que é
   commitado pelo próprio workflow.
3. `index.html` (estático, zero dependências) faz `fetch("dados.json")` e monta
   quadro-resumo, filtros e tabela no navegador. GitHub Pages serve os dois
   arquivos. Nenhum servidor de aplicação envolvido.

Campos de cada contrato no `dados.json`: `n` número, `o` objeto, `f`
fornecedor, `cnpj`, `p` processo, `fim` vigência final, `d` dias até o fim
(negativo = vencido no sistema), `v` valor global, `emp/liq/pag` execução
(somas dos empenhos, incluindo restos a pagar; `liq` = liquidado aguardando
pagamento), `g` gestor(es), `ne` 1 = nota de empenho, `eano` 1 = tem empenho
emitido no ano corrente, `fund` 1 = fundação de apoio, `cid` id interno do
contrato na API (usado nos links).

Base da UG em ago/2026: 2.566 registros "ativos", sendo 1.531 NEs e 1.011
contratos; após filtros do painel, 633 monitorados (372 contratos + 261 NEs).

## API — referências

- Manual (Swagger): `https://contratos.comprasnet.gov.br/api/docs`
  (JSON: `/docs/api-docs.json`). Endpoints usados ficam na seção "Contratos".
- Tela pública de qualquer contrato:
  `https://contratos.comprasnet.gov.br/transparencia/contratos/{cid}` —
  o painel linka o número de cada contrato pra lá.
- `/contrato/{id}/historico` traz aditivos e apostilamentos (não usado na
  carga, útil pra investigar caso a caso).
- Só o `/api/v1` (perfil de gestão) exige credencial — o Guilherme tem, mas a
  carga não precisa. Existe `/api/v1/contrato/responsaveis` (responsáveis em
  lote, por período) se um dia a carga precisar acelerar.

## Decisões tomadas (não desfazer sem conversar)

- Fonte é o Comprasnet Contratos, NÃO a API de Dados Abertos: os Dados Abertos
  ficam desatualizados quando há aditivo de renovação (casos reais: 432/2024 e
  532/2024 constavam vencidos lá, renovados no Comprasnet).
- Janela: vigência final até 730 dias à frente e vencidos há até 180 dias.
  Vencido há mais de 180 dias = encerrado sem baixa, fica fora (havia ~1.800).
- Faixa "Verificar" (roxa) = ativo com vigência vencida no sistema. Fica FORA
  da lista principal; só aparece clicando no card. O tooltip da situação diz se
  o contrato tem empenho no ano (vivo, aditivo não registrado — ex.: TSM
  197/2022) ou não (encerrado sem baixa — maioria fundações). Em ago/2026:
  16 vivos, 48 parados.
- Total monitorado do quadro-resumo conta só vigentes (d ≥ 0), pra bater com a
  lista principal.
- NEs entram por padrão (há contratação real registrada com numeração de NE);
  filtro Instrumento separa quando preciso.
- Coluna Gestor: todos os "Gestor" ativos separados por " / "; sem titular,
  cai pra Gestor Substituto → Fiscal Titular → Fiscal Técnico → Fiscal
  Administrativo, com a função entre parênteses. Só ~13% dos contratos têm
  responsável cadastrado — a coluna vazia é em si uma pendência (designação
  não registrada). A pesquisa busca também por nome de gestor.
- Pago = Pg + RP Pg de todos os empenhos (acumula exercícios; pode passar o
  valor global da vigência atual — esperado, não é bug). Quando passa, a
  barrinha fica hachurada e o tooltip mostra o múltiplo (ex.: "3,8× o valor
  global") em vez de percentual. O `valor_acumulado` da API foi testado como
  denominador e descartado: em 36 de 48 casos vem zerado, igual ao global ou
  sem relação com o contrato.
- Interface enxuta por exigência do Guilherme: sem notas de rodapé, sem linha
  de fonte, sem coluna de dias (dias só no tooltip da situação). Visual sóbrio
  de sistema de governo.

## Próximos passos combinados

- Publicar em domínio da UFG (hoje: GitHub Pages) e manter atualização diária.
- Alerta automático por e-mail quando contrato cruza 180/120/90 dias
  (GitHub Actions + conta institucional com senha de app como secret).
- Vincular gestor ao e-mail institucional (Gmail UFG) — Guilherme vai
  verificar como obter essa lista.

## Contexto de quem usa

Guilherme trabalha na DLOG/PROAD e é gestor dos contratos 532/2024 (Prime,
frota) e 582/2025 (Atlantico, locação de veículos leves). A lista de contratos
da frota (Ticket, TSM, Prime, seguros etc.) é o dia a dia dele; o painel serve
à DLOG e ao departamento de compras.
