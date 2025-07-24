import time

def timing_decorator(func_name=None):
    def actual_decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000
            print(f"{func.__name__ if func_name == None else func_name} took {execution_time:.4f} ms to execute.")
            return result
        return wrapper
    return actual_decorator