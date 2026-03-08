import subprocess
import sys
import os
import time
import random
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

# --- CONFIGURACIÓN DEL EXPERIMENTO ---
SOLVER_SCRIPT = "npuzzle_solver_2.py"
TIMEOUT_SEGS = 300  # 5 minutos
SIZES = [3, 4, 5, 6, 7, 8]
DIFFICULTIES = {
    "Facil (10)": 10,
    "Medio (20)": 20,
    "Dificil (50)": 50
}
NUM_TESTS = 100  # 100 tableros por cada combinación
OUTPUT_DIR = "tableros"   # Carpeta raíz donde se guardarán los tableros
GRAPHS_DIR = "graficas"   # Carpeta donde se guardarán las gráficas


# ─────────────────────────────────────────────
#   UTILIDADES DE GENERACIÓN Y ARCHIVOS
# ─────────────────────────────────────────────

def generate_board(N, moves_count):
    """Genera un tablero meta y lo desordena con movimientos válidos."""
    goal = [[(r * N + c + 1) % (N * N) for c in range(N)] for r in range(N)]
    state = [list(row) for row in goal]

    r0, c0 = N - 1, N - 1
    last_move = None

    for _ in range(moves_count):
        neighbors = []
        if r0 > 0 and last_move != 'D':     neighbors.append((-1, 0, 'U'))
        if r0 < N - 1 and last_move != 'U': neighbors.append((1,  0, 'D'))
        if c0 > 0 and last_move != 'R':     neighbors.append((0, -1, 'L'))
        if c0 < N - 1 and last_move != 'L': neighbors.append((0,  1, 'R'))

        dr, dc, act = random.choice(neighbors)
        nr, nc = r0 + dr, c0 + dc

        state[r0][c0], state[nr][nc] = state[nr][nc], state[r0][c0]
        r0, c0 = nr, nc
        last_move = act

    return tuple(tuple(row) for row in state), tuple(tuple(row) for row in goal)


def create_input_file(N, initial, goal, filepath):
    """Crea el archivo .txt con el formato esperado por el solver."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(f"{N}\n")
        for row in initial:
            f.write(",".join(map(str, row)) + "\n")
        for row in goal:
            f.write(",".join(map(str, row)) + "\n")


def get_instance_path(N, diff_name, iteration):
    """
    Devuelve la ruta completa del archivo de instancia.
    Estructura:  tableros/<NxN>/<dificultad>/instancia_<i>.txt
    """
    size_folder = f"{N}x{N}"
    # Sanitizar nombre de dificultad para usarlo como carpeta
    diff_folder = diff_name.replace(" ", "_").replace("(", "").replace(")", "")
    filename    = f"instancia_{iteration:03d}.txt"
    return os.path.join(OUTPUT_DIR, size_folder, diff_folder, filename)


def parse_output(stdout, elapsed_time):
    """Extrae las métricas de la salida de consola del solver."""
    metrics = {
        "Status":      "Error/No Solución",
        "Movimientos": None,
        "Nodos":       None,
        "Tiempo_seg":  elapsed_time,
        "RAM_KB":      None
    }

    if "✔ RESUELTO" in stdout:
        metrics["Status"] = "Resuelto"

        match_mov = re.search(r"Movimientos\s*:\s*(\d+)", stdout)
        if match_mov:
            metrics["Movimientos"] = int(match_mov.group(1))

        match_nod = re.search(r"Nodos vistos\s*:\s*([\d,]+)", stdout)
        if match_nod:
            metrics["Nodos"] = int(match_nod.group(1).replace(",", ""))

        match_ram = re.search(r"RAM estimada\s*:\s*~([\d.]+)\s*KB", stdout)
        if match_ram:
            metrics["RAM_KB"] = float(match_ram.group(1))

    return metrics


# ─────────────────────────────────────────────
#   EXPERIMENTO PRINCIPAL
# ─────────────────────────────────────────────

def run_experiment():
    results      = []
    total_tests  = len(SIZES) * len(DIFFICULTIES) * NUM_TESTS
    test_counter = 0
    csv_filename = "resultados_brutos.csv"

    print("=== INICIANDO ANÁLISIS EMPÍRICO ===")
    print(f"Total de pruebas: {total_tests}")
    print(f"Instancias guardadas en: ./{OUTPUT_DIR}/")
    print(f"Timeout por prueba    : {TIMEOUT_SEGS} s\n")

    for N in SIZES:
        for diff_name, scramble_moves in DIFFICULTIES.items():
            for i in range(1, NUM_TESTS + 1):
                test_counter += 1

                # Generar tablero y guardar la instancia
                initial, goal     = generate_board(N, scramble_moves)
                instance_filepath = get_instance_path(N, diff_name, i)
                create_input_file(N, initial, goal, instance_filepath)

                print(
                    f"[{test_counter:>4}/{total_tests}] "
                    f"Tablero {N}x{N} | {diff_name} | Prueba {i}... ",
                    end="", flush=True
                )

                # Ejecutar solver
                start_timer = time.time()
                try:
                    process = subprocess.run(
                        [sys.executable, SOLVER_SCRIPT, instance_filepath],
                        capture_output=True,
                        text=True,
                        timeout=TIMEOUT_SEGS
                    )
                    elapsed = time.time() - start_timer
                    metrics = parse_output(process.stdout, elapsed)
                    print(metrics["Status"])

                except subprocess.TimeoutExpired:
                    elapsed = TIMEOUT_SEGS
                    metrics = {
                        "Status":      "Faltó Tiempo",
                        "Movimientos": None,
                        "Nodos":       None,
                        "Tiempo_seg":  TIMEOUT_SEGS,
                        "RAM_KB":      None
                    }
                    print("Faltó Tiempo (Timeout)")

                row = {
                    "Tamaño":     f"{N}x{N}",
                    "N":          N,
                    "Dificultad": diff_name,
                    "Scramble":   scramble_moves,
                    "Iteración":  i,
                    "Archivo":    instance_filepath,
                    **metrics
                }
                results.append(row)

                # Backup incremental
                pd.DataFrame(results).to_csv(csv_filename, index=False)

    print(f"\n✔ Instancias guardadas en ./{OUTPUT_DIR}/")
    print(f"✔ CSV guardado en {csv_filename}\n")
    return pd.DataFrame(results)


# ─────────────────────────────────────────────
#   GENERACIÓN DE GRÁFICAS
# ─────────────────────────────────────────────

def plot_analytics(df: pd.DataFrame, out_dir: str = GRAPHS_DIR):
    """Genera y guarda 5 gráficas analíticas en out_dir."""
    os.makedirs(out_dir, exist_ok=True)
    sns.set_theme(style="whitegrid", palette="muted")

    df_solved = df[df["Status"] == "Resuelto"].copy()

    # ── 1. Tiempo de ejecución ────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(13, 6))
    sns.lineplot(
        data=df_solved, x="N", y="Tiempo_seg",
        hue="Dificultad", marker="o", ax=ax
    )
    ax.set_yscale("log")
    ax.set_title("Tiempo de Ejecución vs Tamaño del Tablero\n(Escala Logarítmica, solo casos resueltos)", fontsize=13)
    ax.set_ylabel("Tiempo (segundos)")
    ax.set_xlabel("N (Dimensión NxN)")
    ax.set_xticks(SIZES)
    ax.legend(title="Dificultad")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "1_tiempos_ejecucion.png"), dpi=150)
    plt.close()
    print("  ✔ 1_tiempos_ejecucion.png")

    # ── 2. Estadística de soluciones (stacked bar) ────────────────────────
    status_counts = (
        df.groupby(["Tamaño", "Dificultad", "Status"])
          .size()
          .unstack(fill_value=0)
          .reset_index()
    )
    for col in ["Resuelto", "Faltó Tiempo", "Error/No Solución"]:
        if col not in status_counts.columns:
            status_counts[col] = 0

    status_counts["Total"] = (
        status_counts["Resuelto"]
        + status_counts["Faltó Tiempo"]
        + status_counts["Error/No Solución"]
    )

    fig, ax = plt.subplots(figsize=(14, 7))
    sns.barplot(
        data=status_counts, x="Tamaño", y="Total",
        hue="Dificultad", color="salmon", alpha=0.85, ax=ax
    )
    sns.barplot(
        data=status_counts, x="Tamaño", y="Resuelto",
        hue="Dificultad", color="mediumseagreen", ax=ax
    )
    resuelto_patch = mpatches.Patch(color="mediumseagreen", label="Resueltos")
    timeout_patch  = mpatches.Patch(color="salmon",         label="Faltó Tiempo / Error")
    ax.legend(handles=[resuelto_patch, timeout_patch], title="Estado")
    ax.set_title("Tasa de Éxito: Resueltos vs Faltó Tiempo\n(100 pruebas por combinación)", fontsize=13)
    ax.set_ylabel("Cantidad de Pruebas")
    ax.set_xlabel("Dimensión del Tablero")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "2_estadistico_soluciones.png"), dpi=150)
    plt.close()
    print("  ✔ 2_estadistico_soluciones.png")

    # ── 3. Nodos visitados ────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.lineplot(
        data=df_solved, x="N", y="Nodos",
        hue="Dificultad", marker="o", ax=ax
    )
    ax.set_yscale("log")
    ax.set_title("Explosión Combinatoria: Nodos Visitados vs Tamaño del Tablero\n(Escala Logarítmica)", fontsize=13)
    ax.set_ylabel("Nodos Visitados")
    ax.set_xlabel("N (Dimensión NxN)")
    ax.set_xticks(SIZES)
    ax.legend(title="Dificultad")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "3_nodos_visitados.png"), dpi=150)
    plt.close()
    print("  ✔ 3_nodos_visitados.png")

    # ── 4. Número de movimientos ──────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(13, 6))
    sns.lineplot(
        data=df_solved, x="N", y="Movimientos",
        hue="Dificultad", marker="o", ax=ax
    )
    ax.set_title("Número de Movimientos en la Solución vs Tamaño del Tablero", fontsize=13)
    ax.set_ylabel("Movimientos (longitud del camino)")
    ax.set_xlabel("N (Dimensión NxN)")
    ax.set_xticks(SIZES)
    ax.legend(title="Dificultad")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "4_movimientos.png"), dpi=150)
    plt.close()
    print("  ✔ 4_movimientos.png")

    # ── 5. Uso de RAM ─────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(13, 6))
    sns.lineplot(
        data=df_solved, x="N", y="RAM_KB",
        hue="Dificultad", marker="o", ax=ax
    )
    ax.set_yscale("log")
    ax.set_title("Uso de Memoria RAM vs Tamaño del Tablero\n(Escala Logarítmica)", fontsize=13)
    ax.set_ylabel("RAM Estimada (KB)")
    ax.set_xlabel("N (Dimensión NxN)")
    ax.set_xticks(SIZES)
    ax.legend(title="Dificultad")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "5_uso_ram.png"), dpi=150)
    plt.close()
    print("  ✔ 5_uso_ram.png")

    print(f"\n✔ Las 5 gráficas se guardaron en ./{out_dir}/\n")


# ─────────────────────────────────────────────
#   GENERACIÓN DE GRÁFICAS DESDE CSV EXISTENTE
# ─────────────────────────────────────────────

def generate_graphs_from_csv(csv_path: str = "resultados_brutos.csv"):
    """
    Carga un CSV existente y genera las gráficas.
    Úsalo si ya corriste el experimento y sólo quieres regenerar las gráficas.
    """
    if not os.path.exists(csv_path):
        print(f"[ERROR] No se encontró el archivo: {csv_path}")
        return

    print(f"Cargando datos de '{csv_path}'...")
    df = pd.read_csv(csv_path)
    print(f"  Filas cargadas: {len(df)}")
    print(f"  Columnas     : {list(df.columns)}\n")

    print("Generando gráficas analíticas...")
    plot_analytics(df)


# ─────────────────────────────────────────────
#   PUNTO DE ENTRADA
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Análisis empírico del N-Puzzle Solver"
    )
    parser.add_argument(
        "--only-graphs",
        action="store_true",
        help="Sólo genera las gráficas a partir de 'resultados_brutos.csv' sin correr el experimento."
    )
    parser.add_argument(
        "--csv",
        default="resultados_brutos.csv",
        help="Ruta del CSV a usar con --only-graphs (default: resultados_brutos.csv)."
    )
    args = parser.parse_args()

    if args.only_graphs:
        # ── Modo: sólo gráficas ──────────────────────────────────────────
        generate_graphs_from_csv(args.csv)
    else:
        # ── Modo: experimento completo + gráficas ────────────────────────
        df = run_experiment()
        print("Generando gráficas analíticas...")
        plot_analytics(df)
        print("¡Análisis Terminado!")
        print(f"  • Tableros  → ./{OUTPUT_DIR}/")
        print(f"  • CSV       → resultados_brutos.csv")
        print(f"  • Gráficas  → ./{GRAPHS_DIR}/")