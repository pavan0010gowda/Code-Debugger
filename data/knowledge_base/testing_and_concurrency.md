# Testing, Verification & Concurrency Best Practices

## Unit Testing Best Practices with PyTest & Unittest
- **Arrange-Act-Assert (AAA) Pattern**:
  - **Arrange**: Set up test inputs, mock fixtures, and preconditions.
  - **Act**: Call the unit or method under test.
  - **Assert**: Verify return values, state mutations, and invariants.
- **Edge-Case Coverage**:
  - Test empty collections (`[]`, `{}`, `""`).
  - Test boundary numbers (`0`, `-1`, `MAX_INT`, floating point infinites).
  - Test None/Null inputs where unexpected.
  - Test expected exception throwing:
    ```python
    import pytest

    def test_divide_by_zero():
        with pytest.raises(ZeroDivisionError):
            safe_divide(10, 0)
    ```
- **Deterministic and Isolated Tests**:
  - Tests should never depend on external network calls or global mutable state.
  - Test execution should yield the same output whether run individually or in a suite.

## Concurrency & Thread Safety
- **Race Conditions**:
  - Multiple threads accessing shared mutable state without synchronization can interleave unpredictably.
  - Always guard shared state using `threading.Lock()` or `threading.RLock()`:
    ```python
    import threading

    counter_lock = threading.Lock()
    def increment():
        with counter_lock:
            global counter
            counter += 1
    ```
- **Deadlocks**:
  - Occur when two threads wait for locks held by each other.
  - Fix by enforcing a strict global lock acquisition order or using timeouts (`lock.acquire(timeout=5.0)`).
- **CPU-bound vs I/O-bound**:
  - Python's Global Interpreter Lock (GIL) limits pure Python bytecode execution to one core per process.
  - For I/O-bound tasks: use `asyncio` or `concurrent.futures.ThreadPoolExecutor`.
  - For CPU-heavy computational workloads: use `multiprocessing` or native C/Rust extensions.

