# Proyecto 2 — Teoría de la Computación

Implementación del Proyecto No. 2 del curso de **Teoría de la Computación**.

El proyecto tiene como objetivo trabajar con una Gramática Independiente del Contexto (GIC/CFG), realizar su preparación para Forma Normal de Chomsky y utilizar el algoritmo CYK para determinar si una frase pertenece al lenguaje generado por la gramática.

## Estado actual

El repositorio contiene actualmente la estructura inicial del proyecto.

La implementación se realizará de forma incremental, separando las responsabilidades de representación de gramáticas, entrada, simplificación, conversión a Forma Normal de Chomsky, algoritmo CYK, reconstrucción del árbol sintáctico y pruebas.

## Estructura

    proyecto2-toc/
    ├── grammars/
    ├── src/
    │   ├── algorithms/
    │   │   ├── chomsky/
    │   │   ├── cyk/
    │   │   └── simplification/
    │   ├── input/
    │   ├── model/
    │   ├── output/
    │   └── utils/
    ├── tests/
    ├── main.py
    ├── README.md
    └── .gitignore

## Componentes planificados

- Representación de gramáticas y producciones.
- Lectura y validación de gramáticas desde archivos de texto.
- Eliminación de producciones-ε.
- Eliminación de producciones unitarias.
- Eliminación de símbolos inútiles.
- Conversión a Forma Normal de Chomsky.
- Validación de la gramática resultante.
- Implementación del algoritmo CYK mediante programación dinámica.
- Reconstrucción del parse tree.
- Medición del tiempo de validación.
- Pruebas unitarias y de integración.

## Gramática principal

La gramática principal del proyecto se almacenará en:

    grammars/english.txt

Además, el directorio `grammars/` contendrá gramáticas auxiliares utilizadas para verificar las distintas etapas de simplificación y conversión.

## Ejecución

La forma final de ejecución será:

    python main.py

El programa utilizará por defecto la gramática principal del proyecto y solicitará textualmente una frase para determinar si pertenece al lenguaje generado por la gramática.

## Pruebas

Las pruebas automatizadas se ejecutarán mediante:

    python -m unittest discover -v

Las pruebas se organizarán por componente para verificar de manera independiente el modelo, la lectura de gramáticas, las transformaciones, la conversión a Forma Normal de Chomsky y el algoritmo CYK.

## Organización general

El proyecto se divide en los siguientes componentes:

- `grammars/`: gramáticas utilizadas por el programa y por las pruebas.
- `src/model/`: estructuras utilizadas para representar gramáticas, producciones y resultados.
- `src/input/`: lectura, validación y procesamiento de la entrada.
- `src/algorithms/simplification/`: algoritmos de simplificación de gramáticas.
- `src/algorithms/chomsky/`: conversión y validación de Forma Normal de Chomsky.
- `src/algorithms/cyk/`: implementación del algoritmo CYK.
- `src/output/`: presentación de resultados y estructuras generadas.
- `src/utils/`: utilidades generales del proyecto.
- `tests/`: pruebas unitarias y de integración.

## Curso

**CC2019 — Teoría de la Computación**  
Universidad del Valle de Guatemala

## Referencias bibliográficas

1. GeeksforGeeks. (2025, 15 de julio). *Cocke–Younger–Kasami (CYK) algorithm*. GeeksforGeeks. https://www.geeksforgeeks.org/compiler-design/cocke-younger-kasami-cyk-algorithm/

2. GeeksforGeeks. (2026, 26 de enero). *Dynamic programming or DP*. GeeksforGeeks. https://www.geeksforgeeks.org/dsa/dynamic-programming/

3. GeeksforGeeks. (2026, 14 de febrero). *Classification of context free grammars*. GeeksforGeeks. https://www.geeksforgeeks.org/compiler-design/classification-of-context-free-grammars/

4. Cocke, J., & Schwartz, J. T. (1970). *Programming languages and their compilers: Preliminary notes* (2.ª ed. rev.). Courant Institute of Mathematical Sciences, New York University. https://softwarepreservation.computerhistory.org/SETL/precursors/Cocke_Schwartz-Programming_Languages_and_Their_Compilers-1970.pdf

5. Kasami, T. (1966). *An efficient recognition and syntax-analysis algorithm for context-free languages* (Coordinated Science Laboratory Report No. R-257). Coordinated Science Laboratory, University of Illinois at Urbana-Champaign. https://www.ideals.illinois.edu/items/100444

> Las referencias de GeeksforGeeks se utilizan como material introductorio y de consulta. Los trabajos de Cocke y Schwartz y de Kasami corresponden a fuentes históricas primarias relacionadas con el desarrollo de los métodos estudiados.
