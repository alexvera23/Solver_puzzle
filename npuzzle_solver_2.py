"""
N-Puzzle Solver — IDA* con heurística admisible
================================================
Entrada : archivo de texto con tablero inicial y meta
Salida  : secuencia de movimientos U/D/L/R, nodos visitados, tiempo, pasos

Formato del archivo de entrada:
  Línea 1     → dimensión N
  Líneas 2..N+1   → tablero inicial  (números separados por comas)
  Líneas N+2..2N+1 → tablero meta    (números separados por comas)

Ejemplo (3×3):
  3
  1,2,3
  8,4,5
  7,6,0
  1,2,3
  8,0,4
  7,6,5

Uso:
  python npuzzle_solver.py <archivo.txt>
"""

import math
import sys
import time

sys.setrecursionlimit(2_000_000)

# ─── CONFIGURACIÓN GLOBAL ─────────────────────────────────────────────────────

HEURISTIC_MODE = "admissible"   # única opción activa; "learned" no garantiza óptimo
MAX_DEPTH_PER_ITERATION: int | None = None   # ← ajustar según necesidad




MOVES    = [(-1, 0, "U"), (1, 0, "D"), (0, -1, "L"), (0, 1, "R")]
OPPOSITE = {"U": "D", "D": "U", "L": "R", "R": "L"}




def read_input(filepath: str):
    """
    Lee el archivo de entrada y devuelve (N, tablero_inicial, tablero_meta).
    Admite separadores coma o espacio en cada fila.
    """
    with open(filepath, "r") as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]

    if len(lines) < 1:
        raise ValueError("Archivo vacío.")

    N = int(lines[0])
    expected = 1 + 2 * N
    if len(lines) < expected:
        raise ValueError(
            f"Se esperaban {expected} líneas (1 + 2×{N}), se encontraron {len(lines)}."
        )

    def parse_row(line: str) -> list[int]:
        sep = "," if "," in line else None
        return list(map(int, line.split(sep)))

    initial = [parse_row(lines[1 + i])     for i in range(N)]
    goal    = [parse_row(lines[1 + N + i]) for i in range(N)]


    for board, name in ((initial, "inicial"), (goal, "meta")):
        for r, row in enumerate(board):
            if len(row) != N:
                raise ValueError(
                    f"Tablero {name}, fila {r}: se esperaban {N} valores, "
                    f"se encontraron {len(row)}."
                )
        flat = tuple(v for row in board for v in row)
        expected_vals = set(range(N * N))
        if set(flat) != expected_vals:
            raise ValueError(
                f"Tablero {name} no contiene exactamente los valores 0..{N*N-1}."
            )

    return N, initial, goal




def flatten(board) -> tuple:
    """Acepta lista/tupla 2-D o 1-D y devuelve tupla plana."""
    if board and hasattr(board[0], "__iter__"):
        return tuple(v for row in board for v in row)
    return tuple(board)


def make_goal_positions(goal_flat: tuple, N: int) -> list:
    """
    Tabla de lookup: gp[val] = (fila_meta, col_meta).
    Funciona con CUALQUIER configuración meta, no solo la estándar.
    """
    W  = N * N
    gp = [None] * W
    for i in range(W):
        val     = goal_flat[i]
        gp[val] = (i // N, i % N)
    return gp


def count_inversions_parity(flat: tuple, N: int) -> int:
    """
    Devuelve la paridad de (inversiones [+ fila_del_vacío_desde_abajo si N par]).
    Sirve para verificar si dos configuraciones son mutuamente alcanzables.
    """
    lst = [v for v in flat if v != 0]
    inv = sum(
        1 for i in range(len(lst))
          for j in range(i + 1, len(lst))
          if lst[i] > lst[j]
    )
    if N % 2 == 0:
        blank_row_from_bottom = N - flat.index(0) // N
        return (inv + blank_row_from_bottom) % 2
    return inv % 2


def is_solvable(initial_flat: tuple, goal_flat: tuple, N: int) -> bool:
    """
    El tablero inicial puede llegar al meta ↔ ambos tienen la misma paridad.
    Funciona para metas arbitrarias (no solo la estándar [1,2,...,0]).
    """
    return (count_inversions_parity(initial_flat, N) ==
            count_inversions_parity(goal_flat,    N))


# ─── HEURÍSTICA: MANHATTAN COMPLETA (para el estado inicial) ─────────────────

def manhattan_full(state: tuple, N: int, gp: list) -> int:
    """
    Calcula la distancia Manhattan completa desde cero — O(N²).
    Solo se llama UNA vez por iteración IDA* (en el nodo raíz).
    Para el resto de nodos se usa la actualización incremental O(1).
    """
    h = 0
    W = N * N
    for i in range(W):
        val = state[i]
        if val == 0:
            continue
        tr, tc = gp[val]
        r,  c  = i // N, i % N
        h += abs(r - tr) + abs(c - tc)
    return h


# ─── HEURÍSTICA: CONFLICTOS LINEALES (filas y columnas) ──────────────────────

def linear_conflicts(state: tuple, N: int, gp: list) -> int:
    """
    Calcula los Conflictos Lineales completos — O(N²).
    Se llama en cada nodo (no tiene actualización incremental trivial),
    pero aporta guía heurística suficientemente valiosa para compensar.
    ✔ Admisible y consistente cuando se suma a Manhattan.
    """
    lc = 0

    # ── Conflictos Lineales — filas ───────────────────────────────────────────
    for r in range(N):
        cols_meta = []
        for c in range(N):
            val = state[r * N + c]
            if val != 0 and gp[val][0] == r:
                cols_meta.append(gp[val][1])
        for i in range(len(cols_meta)):
            for j in range(i + 1, len(cols_meta)):
                if cols_meta[i] > cols_meta[j]:
                    lc += 2

    # ── Conflictos Lineales — columnas ────────────────────────────────────────
    for c in range(N):
        rows_meta = []
        for r in range(N):
            val = state[r * N + c]
            if val != 0 and gp[val][1] == c:
                rows_meta.append(gp[val][0])
        for i in range(len(rows_meta)):
            for j in range(i + 1, len(rows_meta)):
                if rows_meta[i] > rows_meta[j]:
                    lc += 2

    return lc


# ─── MOTOR IDA* CON BÚSQUEDA TABÚ ────────────────────────────────────────────

def solve(initial_board, goal_board):

    flat      = flatten(initial_board)
    goal_flat = flatten(goal_board)
    N         = int(math.isqrt(len(flat)))
    gp        = make_goal_positions(goal_flat, N)

    # ── Casos triviales ───────────────────────────────────────────────────────
    if flat == goal_flat:
        return []

    if not is_solvable(flat, goal_flat, N):
        return None

    # ── Heurística inicial — completa (solo aquí se paga O(N²) para Manhattan) ──
    init_h_man = manhattan_full(flat, N, gp)
    threshold  = init_h_man + linear_conflicts(flat, N, gp)

    blank_idx   = flat.index(0)
    nodes_ev    = [0]           # lista para mutación en closure
    t_start     = time.time()
    action_path: list[str] = []

    """print(f"\n{'='*60}")
    print(f"  IDA* + Tabú — tablero {N}×{N}")
    print(f"  Heurística inicial : {threshold}")
    print(f"  Profundidad máx/iter: "
          f"{'sin límite' if MAX_DEPTH_PER_ITERATION is None else MAX_DEPTH_PER_ITERATION}")
    print(f"{'='*60}")"""

    FOUND = object()   # centinela único; no confundir con int/str

    # ── Búsqueda DFS con poda f > umbral ──────────────────────────────────────
    def search(state: tuple, g: int, threshold: int,
               bi: int, last: str | None, tabu: set,
               h_man: int) -> object:
        nodes_ev[0] += 1

        # Reporte de progreso cada 500 000 nodos
        if nodes_ev[0] % 500_000 == 0:
            elapsed = time.time() - t_start
            print(f"  nodos: {nodes_ev[0]:>12,} | g={g:>4} "
                  f"| umbral={threshold:>4} | {elapsed:.1f}s")

        # ── h = Manhattan (incremental, ya calculado) + LC (completo) ─────────
        h = h_man + linear_conflicts(state, N, gp)
        f = g + h

        # ── Poda por umbral ───────────────────────────────────────────────────
        if f > threshold:
            return f

        # ── Poda por profundidad máxima por iteración ─────────────────────────
        if MAX_DEPTH_PER_ITERATION is not None and g >= MAX_DEPTH_PER_ITERATION:
            return math.inf

        # ── ¿Meta alcanzada? ──────────────────────────────────────────────────
        if state == goal_flat:
            return FOUND

        min_t   = math.inf
        r0, c0  = bi // N, bi % N

        for dr, dc, act in MOVES:
            # Poda de movimiento inverso inmediato
            if last is not None and OPPOSITE[last] == act:
                continue

            nr, nc = r0 + dr, c0 + dc
            if not (0 <= nr < N and 0 <= nc < N):
                continue

            new_bi = nr * N + nc

            # ── Actualización incremental de Manhattan — O(1) ─────────────────
            # La ficha que se mueve es state[new_bi]; va de new_bi → bi.
            tile_val    = state[new_bi]
            tr, tc      = gp[tile_val]
            # Posición actual de la ficha (antes del intercambio)
            old_r, old_c = new_bi // N, new_bi % N
            # Posición nueva de la ficha (donde estaba el blank)
            new_r, new_c = r0, c0
            # Contribución Manhattan vieja y nueva de esa ficha
            man_old = abs(old_r - tr) + abs(old_c - tc)
            man_new = abs(new_r - tr) + abs(new_c - tc)
            # Manhattan actualizada del hijo en O(1)
            child_h_man = h_man - man_old + man_new

            lst    = list(state)
            lst[bi], lst[new_bi] = lst[new_bi], lst[bi]
            new_s  = tuple(lst)

            # ── Búsqueda Tabú: no volver a un estado del camino actual ────────
            if new_s in tabu:
                continue

            # Expandir
            action_path.append(act)
            tabu.add(new_s)

            res = search(new_s, g + 1, threshold, new_bi, act, tabu, child_h_man)

            # ── Si se encontró la meta, NO revertir: preservar el camino ─────
            if res is FOUND:
                return FOUND

            # Retroceder (backtrack): solo si NO encontramos la meta
            tabu.discard(new_s)
            action_path.pop()

            if isinstance(res, (int, float)) and res < min_t:
                min_t = res

        return min_t

    # ── Iteración de umbrales ─────────────────────────────────────────────────
    tabu = {flat}   # el estado inicial siempre está en el camino
    while True:
        result = search(flat, 0, threshold, blank_idx, None, tabu, init_h_man)

        if result is FOUND:
            elapsed = time.time() - t_start
            depth   = len(action_path)
            ram_kb  = (depth + 1) * N * N * 8 / 1024
            """print(f"\n  ✔ RESUELTO")
            print(f"  Movimientos : {depth}")
            print(f"  Nodos vistos: {nodes_ev[0]:,}")
            print(f"  Tiempo      : {elapsed:.4f}s")
            print(f"  RAM estimada: ~{ram_kb:.1f} KB")"""
            return list(action_path)

        if result == math.inf:
            print("\n  ✘ Sin solución alcanzable con la profundidad configurada.")
            return None

        #print(f"  umbral: {threshold:>4} → {result}")
        threshold = result
        # Recalcular h_man del estado inicial para la nueva iteración
        # (h_man no cambia entre iteraciones; el estado raíz es siempre el mismo)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Uso: python npuzzle_solver.py <archivo_entrada.txt>")
        print()
        print("Formato del archivo:")
        print("  Línea 1        : dimensión N")
        print("  Líneas 2..N+1  : tablero inicial (valores 0..N²-1, separados por coma)")
        print("  Líneas N+2..2N+1: tablero meta   (misma convención)")
        sys.exit(1)

    filepath = sys.argv[1]

    # ── Leer entrada ──────────────────────────────────────────────────────────
    try:
        N, initial, goal = read_input(filepath)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error leyendo '{filepath}': {exc}")
        sys.exit(1)

    #print(f"\nTablero inicial ({N}×{N}):")
    for row in initial:
        print("  ", row)
    #print(f"\nTablero meta ({N}×{N}):")
    for row in goal:
        print("  ", row)

    # ── Resolver ──────────────────────────────────────────────────────────────
    solution = solve(initial, goal)

    # ── Imprimir resultado ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    if solution is None:
        print("  RESULTADO: El puzzle no tiene solución.")
    elif solution == []:
        print("  RESULTADO: El tablero ya estaba resuelto. (0 movimientos)")
    else:
        print(f"  RESULTADO: {','.join(solution)}")
        print(f"  Total de movimientos: {len(solution)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()