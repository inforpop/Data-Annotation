"""Computação Clássica — anotação de sentimento em textos (PT-BR).

Fluxo de "model-assisted labeling": um classificador simples por léxico gera
uma pré-anotação; a pessoa anotadora confirma ou corrige. Cada item tem também
um gabarito (gold) para medir a qualidade da anotação.
"""
import re
import unicodedata

LABELS = ["positivo", "neutro", "negativo"]

# (id, texto, gabarito)
DATASET = [
    ("c01", "O atendimento foi excelente e a entrega chegou antes do prazo.", "positivo"),
    ("c02", "Produto quebrou na primeira semana, péssima qualidade.", "negativo"),
    ("c03", "Recebi o pedido hoje. A caixa é azul.", "neutro"),
    ("c04", "Adorei o curso, o professor explica muito bem!", "positivo"),
    ("c05", "O aplicativo trava toda hora, não recomendo.", "negativo"),
    ("c06", "A reunião foi remarcada para quinta-feira às 14h.", "neutro"),
    ("c07", "Ótimo custo-benefício, comprarei novamente.", "positivo"),
    ("c08", "O suporte demorou três dias para responder e não resolveu.", "negativo"),
    ("c09", "O relatório tem doze páginas e dois anexos.", "neutro"),
    ("c10", "Não é ruim, mas esperava mais pelo preço.", "negativo"),
    ("c11", "Interface simples e rápida, fiquei satisfeito.", "positivo"),
    ("c12", "A loja abre às 9h e fecha às 18h.", "neutro"),
    ("c13", "Não gostei nada do acabamento.", "negativo"),
    ("c14", "Não tive nenhum problema, tudo funcionou perfeitamente.", "positivo"),
    ("c15", "O sistema foi atualizado para a versão 2.4.", "neutro"),
    ("c16", "Que decepção, o filme é lento e cansativo.", "negativo"),
    ("c17", "A equipe é atenciosa e muito competente.", "positivo"),
    ("c18", "O pacote saiu do centro de distribuição.", "neutro"),
    ("c19", "Funciona, porém a bateria dura pouco.", "negativo"),
    ("c20", "Recomendo de olhos fechados, maravilhoso!", "positivo"),
]

POSITIVE = {
    "excelente", "adorei", "otimo", "bem", "satisfeito", "simples", "rapida",
    "perfeitamente", "recomendo", "maravilhoso",
    "bom", "boa", "gostei", "antes",
}
NEGATIVE = {
    "pessima", "quebrou", "trava", "ruim", "demorou", "decepcao", "lento",
    "cansativo", "problema", "nao", "gostei",
}
NEGATORS = {"nao", "nunca", "nenhum", "nada"}


def _normalize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.findall(r"[a-z]+", text)


def model_predict(text):
    """Classificador por léxico com tratamento ingênuo de negação.

    É propositalmente imperfeito: serve para mostrar no dashboard a diferença
    entre a pré-anotação automática e o rótulo humano (kappa, matriz etc.).
    """
    tokens = _normalize(text)
    score = 0
    for i, tok in enumerate(tokens):
        negated = i > 0 and tokens[i - 1] in NEGATORS
        if tok in POSITIVE and tok not in NEGATORS:
            score += -1 if negated else 1
        elif tok in NEGATIVE and tok not in NEGATORS:
            score += 1 if negated else -1
        elif tok in NEGATORS:
            score -= 0.5
    if score >= 1:
        return "positivo"
    if score <= -1:
        return "negativo"
    return "neutro"


ITEMS = {
    item_id: {"id": item_id, "text": text, "gold": gold, "model": model_predict(text)}
    for item_id, text, gold in DATASET
}


def public_item(item):
    """Item como enviado ao navegador (sem o gabarito)."""
    return {"id": item["id"], "text": item["text"], "suggestion": item["model"]}
