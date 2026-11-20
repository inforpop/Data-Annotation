"""Métricas de qualidade de anotação (sem dependências externas)."""
from collections import Counter


def accuracy(y_true, y_pred):
    if not y_true:
        return None
    return sum(a == b for a, b in zip(y_true, y_pred)) / len(y_true)


def cohen_kappa(a, b, labels):
    """Kappa de Cohen: concordância entre dois "anotadores" descontando o acaso."""
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[l] / n) * (cb[l] / n) for l in labels)
    if pe == 1:
        return 1.0
    return (po - pe) / (1 - pe)


def confusion(y_true, y_pred, labels):
    idx = {l: i for i, l in enumerate(labels)}
    m = [[0] * len(labels) for _ in labels]
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            m[idx[t]][idx[p]] += 1
    return m


def summarize(rows, total_items, labels):
    human = [r["label"] for r in rows]
    model = [r["model_label"] for r in rows]
    gold = [r["gold_label"] for r in rows]
    secs = [r["seconds"] for r in rows if r.get("seconds")]
    annotators = Counter(r["annotator"] for r in rows)

    def pct(x):
        return None if x is None else round(100 * x, 1)

    def rnd(x):
        return None if x is None else round(x, 3)

    return {
        "total_items": total_items,
        "annotations": len(rows),
        "annotators": dict(annotators),
        "progress_pct": round(100 * len({r["item_id"] for r in rows}) / total_items, 1)
        if total_items else 0,
        "label_distribution": {l: human.count(l) for l in labels},
        "accuracy_human_vs_gold": pct(accuracy(gold, human)),
        "accuracy_model_vs_gold": pct(accuracy(gold, model)),
        "kappa_human_vs_model": rnd(cohen_kappa(human, model, labels)),
        "kappa_human_vs_gold": rnd(cohen_kappa(human, gold, labels)),
        "corrections": sum(h != m for h, m in zip(human, model)),
        "avg_seconds": round(sum(secs) / len(secs), 1) if secs else None,
        "labels": labels,
        "confusion_human_vs_gold": confusion(gold, human, labels),
    }
