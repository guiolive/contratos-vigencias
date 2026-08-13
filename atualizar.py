#!/usr/bin/env python3
"""Atualiza dados.json com os contratos da UFG (órgão 26235) vencendo nos
próximos 24 meses, via API de Dados Abertos do Compras.gov.br.
Executado diariamente pela GitHub Action (.github/workflows/atualizar.yml)."""

import json
import time
import datetime
import urllib.request

BASE = "https://dadosabertos.compras.gov.br/modulo-contratos/1.2_consultarContratos_FimVigencia"
ORGAO = "26235"   # UFG (código SIAFI)
JANELA_DIAS = 730


def baixar():
    hoje = datetime.date.today()
    fim = hoje + datetime.timedelta(days=JANELA_DIAS)
    todos, pagina, total_paginas = [], 1, 1
    while pagina <= total_paginas and pagina <= 10:
        url = (f"{BASE}?pagina={pagina}&tamanhoPagina=500&codigoOrgao={ORGAO}"
               f"&dataVigenciaFinalMin={hoje}&dataVigenciaFinalMax={fim}")
        req = urllib.request.Request(url, headers={"accept": "application/json"})
        for tentativa in range(4):
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    d = json.load(r)
                break
            except Exception:
                time.sleep(6 * (tentativa + 1))
        else:
            raise SystemExit(f"Falha na página {pagina} após 4 tentativas")
        total_paginas = d.get("totalPaginas", 1)
        todos += [c for c in d.get("resultado", []) if not c.get("contratoExcluido")]
        pagina += 1
        time.sleep(1.5)
    return todos, hoje


def preparar(todos, hoje):
    vistos, uniq = set(), []
    for c in todos:
        k = (c["numeroContrato"], c.get("codigoUnidadeGestoraOrigemContrato"))
        if k not in vistos:
            vistos.add(k)
            uniq.append(c)
    dados = []
    for c in uniq:
        fim = c["dataVigenciaFinal"][:10]
        dias = (datetime.date.fromisoformat(fim) - hoje).days
        forn = c.get("nomeRazaoSocialFornecedor") or ""
        dados.append({
            "n": c["numeroContrato"],
            "o": (c.get("objeto") or "")[:160],
            "f": forn[:60],
            "cnpj": c.get("niFornecedor") or "",
            "p": c.get("processo") or "",
            "fim": fim,
            "d": dias,
            "v": round(c.get("valorGlobal") or 0, 2),
            "mod": c.get("nomeModalidadeCompra") or "",
            "fund": 1 if "FUNDACAO" in forn.upper() else 0,
        })
    dados.sort(key=lambda x: x["d"])
    return dados


if __name__ == "__main__":
    todos, hoje = baixar()
    dados = preparar(todos, hoje)
    pacote = {"geradoEm": hoje.isoformat(), "orgao": ORGAO, "ug": "153052",
              "contratos": dados}
    with open("dados.json", "w", encoding="utf-8") as f:
        json.dump(pacote, f, ensure_ascii=False)
    print(f"{len(dados)} contratos gravados em dados.json (posição {hoje})")
