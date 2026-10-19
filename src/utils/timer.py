"""Utilidades de medición de tiempo basadas en time.perf_counter_ns."""

from statistics import median
from time import perf_counter_ns


def measure_ns(operation):
    """Ejecuta `operation` una vez y devuelve (resultado, nanosegundos transcurridos)."""
    start = perf_counter_ns()
    result = operation()
    end = perf_counter_ns()
    return result, end - start


def median_ns(samples):
    """Devuelve la mediana de las muestras; puede ser float si la cantidad es par."""
    return median(samples)
