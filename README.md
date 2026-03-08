Solucionador N-Puzzle (IDA*) y Análisis Empírico

Este repositorio contiene un motor de resolución de alto rendimiento para el clásico problema del N-Puzzle (desde $3\times3$ hasta $8\times8$), implementado en Python puro.

Utiliza el algoritmo de búsqueda IDA* (Iterative Deepening A*) enriquecido con una Búsqueda Tabú Activa y una heurística híbrida admisible (Distancia Manhattan Incremental en $O(1)$ + Conflictos Lineales). Además, incluye un entorno de pruebas masivas (experiment_runner.py) capaz de generar miles de instancias, resolverlas y generar análisis estadísticos automáticos.

 Uso del Solucionador (npuzzle_solver.py)

Para resolver una instancia específica del N-Puzzle, ejecuta el script principal pasando como argumento la ruta del archivo .txt que contiene la configuración del tablero.

python npuzzle_solver_2.py ruta/al/archivo.txt

Ejemplo: python npuzzle_solver_2.py tablero.txt (si el .txt está en el mismo directorio que el programa) 


Formato del archivo txt:

Línea 1: Dimensión $N$ del tablero.

Siguientes $N$ líneas: Tablero inicial (valores separados por comas, 0 = espacio vacío).

Siguientes $N$ líneas: Tablero meta.

Entorno de Análisis Empírico (experiment_runner.py)

El script analista automatiza la generación de tableros, su resolución y la captura de métricas (Tiempo, Nodos visitados, RAM, Movimientos).

Requiere la instalación de las dependencias de análisis:

pip install pandas matplotlib seaborn


Comandos de Ejecución

Correr el experimento completo (Genera tableros, resuelve y grafica):

python runner.py


Generar solo las gráficas (Si ya tienes un CSV generado en una corrida anterior):

python runner.py --only-graphs


Generar gráficas desde un CSV específico:

python experiment_runner.py --only-graphs --csv mis_resultados.csv

 Organización de Carpetas

La arquitectura de generación de datos y resultados del proyecto sigue esta estructura automatizada:

tableros/<NxN>/<Dificultad>/instancia_XXX.txt: Cada instancia generada aleatoriamente se guarda aquí automáticamente. La creación de subcarpetas es manejada dinámicamente por el script. (Nota: Esta carpeta está ignorada en Git para no saturar el repositorio).

graficas/: Contiene los 5 gráficos analíticos generados tras ejecutar el experimento.

Gráficas Analíticas Generadas

1_tiempos_ejecucion.png: Boxplot del tiempo de ejecución por tamaño de tablero y dificultad (representado en escala logarítmica para ilustrar la explosión combinatoria).

2_estadistico_soluciones.png: Gráfico de barras apiladas que contrasta la tasa de tableros Resueltos frente a los que alcanzaron el límite de tiempo (Timeout).

3_nodos_visitados.png: Gráfico de líneas detallando la cantidad de nodos visitados en función de $N$ (escala logarítmica).

4_movimientos.png: Violin plot que muestra la distribución de la longitud de la solución (cantidad de pasos requeridos) según la dificultad.

5_uso_ram.png: Panel dual con un Boxplot del consumo de memoria RAM y un scatter plot relacionando la RAM con los nodos expandidos, demostrando la alta eficiencia del control de memoria Tabú.
