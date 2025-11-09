#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import glob
import json
import argparse
from collections import defaultdict

import matplotlib.pyplot as plt


def parse_args():
    p = argparse.ArgumentParser(description="Tracer success_rate vs norme par direction et shape + plot global")
    p.add_argument("--base", default="results_evaluation",
                   help="Dossier contenant les fichiers result_evaluation_*.json")
    p.add_argument("--agent", default="agents/agent_TD3_2025-05-07_15-48",
                   help="Nom de l'agent sous la clé 'agents/<AGENT>/' (ou racine si tes JSON sont plats)")
    p.add_argument("--save", action="store_true",
                   help="Sauver les figures en PNG (dans fig/)")
    p.add_argument("--dpi", type=int, default=200, help="DPI pour l'export PNG")
    return p.parse_args()


def safe_get_success_rate(d, agent_key):
    """
    Essaie d'abord la structure: {"agents": {agent_key: {"success_rate": ...}}}
    Puis tolère: {agent_key: {"success_rate": ...}}.
    """
    try:
        return d["agents"][agent_key]["success_rate"]
    except Exception:
        pass
    try:
        return d[agent_key]["success_rate"]
    except Exception:
        return None


def parse_norm(norm_str):
    """
    Convertit '0.50' -> 0.5, '050' -> 0.5, '056' -> 0.56, '1' -> 1.0, etc.
    Heuristique : si pas de point et valeur entière > 1, on /100.
    """
    if "." in norm_str:
        return float(norm_str)
    try:
        val = int(norm_str)
        return val / 100.0 if val > 1 else float(val)
    except ValueError:
        return float(norm_str)


def set_scientific_style():
    plt.rcParams.update({
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.linestyle": "--",
        "grid.alpha": 0.4,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.frameon": False,
        "figure.dpi": 120,
    })


def make_output_dir():
    outdir = "fig"
    os.makedirs(outdir, exist_ok=True)
    return outdir


def main():
    args = parse_args()
    set_scientific_style()

    base = args.base
    agent_key = args.agent
    outdir = make_output_dir() if args.save else None

    rx = re.compile(
        r"result_evaluation_(?P<dir>east|west|north|south)_(?P<norm>[0-9]+(?:\.[0-9]+)?)_(?P<shape>[a-zA-Z]+)\.json$"
    )

    # by_dirshape[(direction, shape)] = [(norm, success_rate), ...]
    by_dirshape = defaultdict(list)
    files = sorted(glob.glob(os.path.join(base, "result_evaluation_*.json")))
    missing = []

    if not files:
        print(f"[WARN] Aucun fichier trouvé sous {base}/")
        return

    for fp in files:
        fname = os.path.basename(fp)
        m = rx.match(fname)
        if not m:
            continue

        direction = m.group("dir")
        shape = m.group("shape")  # 'line' ou 'ondulating'
        norm = parse_norm(m.group("norm"))

        try:
            with open(fp, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[ERR] Lecture JSON échouée: {fname} -> {e}")
            continue

        sr = safe_get_success_rate(data, agent_key)
        if sr is None:
            missing.append(fname)
            continue

        by_dirshape[(direction, shape)].append((norm, sr))

    if missing:
        print("[INFO] Fichiers sans success_rate pour cet agent :")
        for x in missing:
            print("  -", x)

    if not by_dirshape:
        print("[WARN] Aucune donnée exploitable.")
        return

    for (direction, shape), pairs in sorted(by_dirshape.items()):
        if direction=='east':
            continue
        pairs.sort(key=lambda x: x[0])  # trier par norme
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]

        plt.figure()
        plt.plot(xs, ys, marker="o", linewidth=1.5, markersize=5)
        plt.xlabel(r"$\|u\|/U$")
        plt.ylabel("Success rate")
        plt.title(f"{direction.capitalize()} — {shape}")
        plt.ylim(0.0, 1.0)  # taux de succès en [0,1]
        plt.xlim(min(xs) - 0.02, max(xs) + 0.02)

        if args.save:
            out = os.path.join(outdir, f"plot_{direction}_{shape}.png")
            plt.savefig(out, dpi=args.dpi, bbox_inches="tight")
            print(f"[OK] Figure sauvegardée: {out}")
        else:
            plt.show()

    # Palette sobre et fixe par direction
    color_map = {
        "east":  "#1f77b4",  # bleu
        "west":  "#d62728",  # rouge
        "north": "#2ca02c",  # vert
        "south": "#ff7f0e",  # orange
    }
    # Marqueurs distincts par shape
    marker_map = {
        "line": "o",
        "ondulating": "s",
    }

    # Regroupement des points pour la légende combinée
    plt.figure()
    # Pour construire une légende claire (couleurs et marqueurs), on trace en boucles séparées
    for (direction, shape), pairs in sorted(by_dirshape.items()):
        if not pairs:
            continue
        if direction =='east':
            continue
        pairs.sort(key=lambda x: x[0])
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]

        c = color_map.get(direction, "#7f7f7f")
        m = marker_map.get(shape, "o")

        # Scatter lisible; linewidths léger pour le contour
        plt.scatter(xs, ys,
                    marker=m, edgecolors="none", s=36, c=c)

        # Optionnel : relier par une ligne fine pour guider l'œil (même couleur, alpha léger)
        plt.plot(xs, ys, linewidth=1.0, alpha=0.6, c=c)

    plt.xlabel(r"$\|u\|/U$")
    plt.ylabel("Success rate")
    plt.ylim(0.0, 1.1)

    # Déterminer les bornes x globales
    all_x = [x for pairs in by_dirshape.values() for (x, _) in pairs]
    if all_x:
        plt.xlim(min(all_x) - 0.02, max(all_x) + 0.02)


    if args.save:
        out = os.path.join(outdir, "plot_global.png")
        plt.savefig(out, dpi=args.dpi, bbox_inches="tight")
        print(f"[OK] Figure sauvegardée: {out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()