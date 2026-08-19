#!/usr/bin/env python3
"""Atualiza dados.json com os contratos ativos da UFG (UG 153052) no
Comprasnet Contratos: vigências (reflete aditivos de renovação) e execução
financeira (empenhado/liquidado/pago, somados dos empenhos).
Executado diariamente pela GitHub Action (.github/workflows/atualizar.yml)."""

import json
import time
import datetime
import urllib.request

CONTRATOS_API = "https://contratos.comprasnet.gov.br/api"
ORGAO = "26235"   # UFG (código SIAFI)
UG = "153052"
JANELA_DIAS = 730
VENCIDO_MAX_DIAS = 180   # vencidos há mais tempo = encerrados sem baixa no sistema


def _get_json(url, timeout=120, tentativas=4):
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    for tentativa in range(tentativas):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception:
            time.sleep(6 * (tentativa + 1))
    return None


def _brl(s):
    """'7.389.247,33' -> 7389247.33"""
    if not s:
        return 0.0
    try:
        return float(str(s).replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def baixar():
    """Lista completa de contratos ativos da UG (sem paginação; demora ~2 min)."""
    hoje = datetime.date.today()
    ativos = _get_json(f"{CONTRATOS_API}/contrato/ug/{UG}", timeout=600)
    if not ativos:
        raise SystemExit("Falha ao consultar contratos ativos no Comprasnet Contratos")
    return ativos, hoje


def preparar(ativos, hoje):
    """Contratos ativos com vigência final até JANELA_DIAS à frente.
    Inclui os vencidos há até VENCIDO_MAX_DIAS que seguem ativos (dias
    negativos) — normalmente aditivo de renovação ainda não registrado.
    Vencidos mais antigos são encerrados sem baixa e ficam de fora.
    Numero repetido (evento antigo + aditivo de renovação): fica o registro
    de vigência mais longa, independente da ordem em que a API devolve."""
    melhores = {}
    for c in ativos:
        fim = (c.get("vigencia_fim") or "")[:10]
        n = c.get("numero")
        if not fim or not n:
            continue
        if n not in melhores or fim > (melhores[n].get("vigencia_fim") or "")[:10]:
            melhores[n] = c
    dados = []
    for n, c in melhores.items():
        fim = (c.get("vigencia_fim") or "")[:10]
        dias = (datetime.date.fromisoformat(fim) - hoje).days
        if dias > JANELA_DIAS or dias < -VENCIDO_MAX_DIAS:
            continue
        forn = ((c.get("fornecedor") or {}).get("nome") or "")
        dados.append({
            "n": n,
            "o": (c.get("objeto") or "")[:160],
            "f": forn[:60],
            "cnpj": (c.get("fornecedor") or {}).get("cnpj_cpf_idgener") or "",
            "p": c.get("processo") or "",
            "fim": fim,
            "d": dias,
            "v": round(_brl(c.get("valor_global")), 2),
            "mod": c.get("modalidade") or "",
            "fund": 1 if "FUNDACAO" in forn.upper() else 0,
            "ne": 1 if c.get("tipo") == "Empenho" else 0,
            "cid": c.get("id"),
        })
    dados.sort(key=lambda x: x["d"])
    return dados


def _nome(usuario):
    """'***.843.731-** - ARETUZA ALVES MARCÓRIO' -> 'ARETUZA ALVES MARCÓRIO'"""
    return usuario.split(" - ", 1)[-1].strip() if usuario else ""


def execucao(dados):
    """Complementa cada contrato com emp/liq/pag (execução financeira, somada
    dos empenhos; `liq` = liquidado aguardando pagamento; inclui restos a
    pagar) e com o gestor titular cadastrado no Comprasnet. Falha de um
    contrato não derruba a rodada."""
    achados = 0
    for c in dados:
        emps = _get_json(f"{CONTRATOS_API}/contrato/{c['cid']}/empenhos", tentativas=3)
        if emps is not None:
            ano = str(datetime.date.today().year)
            c["eano"] = 1 if any((e.get("numero") or "").startswith(ano) for e in emps) else 0
            c["emp"] = round(sum(_brl(e.get("empenhado")) + _brl(e.get("rpinscrito")) for e in emps), 2)
            c["liq"] = round(sum(_brl(e.get("liquidado")) + _brl(e.get("rpliquidado")) for e in emps), 2)
            c["pag"] = round(sum(_brl(e.get("pago")) + _brl(e.get("rppago")) for e in emps), 2)
            achados += 1
        resp = _get_json(f"{CONTRATOS_API}/contrato/{c['cid']}/responsaveis", tentativas=2)
        if resp:
            ativos = [p for p in resp if p.get("situacao") == "Ativo"]
            gestores = [_nome(p.get("usuario")) for p in ativos if p.get("funcao_id") == "Gestor"]
            if gestores:
                c["g"] = " / ".join(gestores)
            else:
                for funcao in ("Gestor Substituto", "Fiscal Titular", "Fiscal Técnico", "Fiscal Administrativo"):
                    quem = next((p for p in ativos if p.get("funcao_id") == funcao), None)
                    if quem:
                        c["g"] = f"{_nome(quem.get('usuario'))} ({funcao.lower()})"
                        break
        time.sleep(0.3)
    print(f"Execução financeira obtida para {achados} de {len(dados)} contratos")
    return achados


if __name__ == "__main__":
    ativos, hoje = baixar()
    dados = preparar(ativos, hoje)
    achados = execucao(dados)
    # queda da API no meio da rodada: aborta sem gravar, senão o painel
    # publica um dia inteiro sem execução financeira e sem gestores
    if dados and achados < 0.9 * len(dados):
        raise SystemExit(
            f"Só {achados} de {len(dados)} contratos com execução obtida "
            "(mínimo 90%) — abortando sem gravar dados.json")
    pacote = {"geradoEm": hoje.isoformat(), "orgao": ORGAO, "ug": UG,
              "contratos": dados}
    with open("dados.json", "w", encoding="utf-8") as f:
        json.dump(pacote, f, ensure_ascii=False)
    print(f"{len(dados)} contratos gravados em dados.json (posição {hoje})")
