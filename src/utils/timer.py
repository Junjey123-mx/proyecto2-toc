from statistics import median
from time import perf_counter_ns


def measure_ns(operation):
    start = perf_counter_ns()
    result = operation()
    end = perf_counter_ns()
    return result, end - start


def median_ns(samples):
    return median(samples)
