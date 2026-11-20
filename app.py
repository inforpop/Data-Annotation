"""🏷️ Data Annotation em Python — Computação Clássica x Computação Quântica.

Autor: Pedro Paulo Ribeiro — www.inforpop.com
"""
import csv
import io
import json
import os

from flask import Flask, Response, abort, jsonify, render_template, request

from annotation import DOMAINS, storage
from annotation.metrics import summarize

app = Flask(__name__)
storage.init_db()

CONTACTS = {
    "site": ("www.inforpop.com", "https://www.inforpop.com"),
    "whatsapp": ("55 21 99961-8643", "https://wa.me/5521999618643"),
    "email": ("inforpop@hotmail.com", "mailto:inforpop@hotmail.com"),
    "linkedin": ("Pedro Paulo Ribeiro",
                 "https://www.linkedin.com/in/pedro-paulo-ribeiro-pcd-1451498/"),
}


def _domain(name):
    if name not in DOMAINS:
        abort(404, description="Domínio inválido. Use 'classical' ou 'quantum'.")
    return DOMAINS[name]


def _annotator():
    name = (request.args.get("annotator") or (request.get_json(silent=True) or {}).get("annotator")
            or "anônimo").strip()
    return name[:40] or "anônimo"


@app.route("/")
def index():
    return render_template(
        "index.html",
        contacts=CONTACTS,
        labels={k: m.LABELS for k, m in DOMAINS.items()},
        totals={k: len(m.ITEMS) for k, m in DOMAINS.items()},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/<domain>/next")
def next_item(domain):
    mod = _domain(domain)
    done = storage.done_ids(domain, _annotator())
    pending = [i for i in mod.ITEMS if i not in done]
    if not pending:
        return jsonify({"finished": True, "total": len(mod.ITEMS)})
    item = mod.ITEMS[pending[0]]
    return jsonify({
        "finished": False,
        "item": mod.public_item(item),
        "position": len(done) + 1,
        "total": len(mod.ITEMS),
    })


@app.post("/api/<domain>/annotate")
def annotate(domain):
    mod = _domain(domain)
    data = request.get_json(silent=True) or {}
    item = mod.ITEMS.get(data.get("item_id"))
    label = data.get("label")
    if item is None or label not in mod.LABELS:
        return jsonify({"error": "item_id ou label inválido", "labels": mod.LABELS}), 400
    seconds = data.get("seconds")
    try:
        seconds = round(float(seconds), 2) if seconds is not None else None
    except (TypeError, ValueError):
        seconds = None
    storage.save(domain, item["id"], _annotator(), label, item["model"], item["gold"], seconds)
    # Feedback pedagógico: depois de anotar, revela o gabarito
    feedback = {"gold": item["gold"], "correct": label == item["gold"]}
    if domain == "quantum":
        feedback["concurrence"] = item["concurrence"]
    return jsonify({"saved": True, "feedback": feedback})


@app.get("/api/<domain>/stats")
def stats(domain):
    mod = _domain(domain)
    annotator = request.args.get("annotator") or None
    rows = storage.fetch(domain, annotator)
    return jsonify(summarize(rows, len(mod.ITEMS), mod.LABELS))


@app.post("/api/<domain>/reset")
def reset(domain):
    _domain(domain)
    storage.clear(domain, _annotator())
    return jsonify({"reset": True})


def _export_rows(domain):
    mod = DOMAINS[domain]
    rows = storage.fetch(domain)
    for r in rows:
        item = mod.ITEMS[r["item_id"]]
        r["content"] = item["text"] if domain == "classical" else item["diagram"]
    return rows


@app.get("/api/<domain>/export.json")
def export_json(domain):
    _domain(domain)
    body = json.dumps(_export_rows(domain), ensure_ascii=False, indent=2)
    return Response(body, mimetype="application/json",
                    headers={"Content-Disposition": f"attachment; filename=anotacoes_{domain}.json"})


@app.get("/api/<domain>/export.csv")
def export_csv(domain):
    _domain(domain)
    rows = _export_rows(domain)
    buf = io.StringIO()
    fields = ["id", "domain", "item_id", "annotator", "label", "model_label",
              "gold_label", "seconds", "created_at", "content"]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    # BOM para o Excel abrir acentos corretamente
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=anotacoes_{domain}.csv"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
