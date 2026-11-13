# Common Python Bugs, Logic Pitfalls & Runtime Traps

## 1. Mutable Default Arguments
- **Pitfall**: In Python, default parameter values are evaluated once when the function definition is executed, NOT each time the function is called.
- **Buggy Code**:
  ```python
  def append_to_cache(item, cache=[]):
      cache.append(item)
      return cache
  ```
- **Correction**: Use `None` as the default sentinel and initialize inside the function:
  ```python
  def append_to_cache(item, cache=None):
      if cache is None:
          cache = []
      cache.append(item)
      return cache
  ```

## 2. Modifying a Collection While Iterating Over It
- **Pitfall**: Removing or inserting elements into a list or dictionary while iterating directly over it leads to skipped elements or `RuntimeError: dictionary changed size during iteration`.
- **Buggy Code**:
  ```python
  for item in items:
      if item % 2 == 0:
          items.remove(item)
  ```
- **Correction**: Iterate over a copy (`items[:]`), use list comprehension (`items = [x for x in items if x % 2 != 0]`), or collect items to remove in a separate set.

## 3. Off-by-One Errors in Slicing and Ranges
- **Pitfall**: `range(start, stop)` is half-open: `[start, stop)` (inclusive of start, exclusive of stop). Slicing `list[0:len(list)-1]` misses the final item.
- **Correction**: Be mindful of half-open intervals. Slicing to the end is simply `list[:]` or `list[start:]`.

## 4. Late Binding Closures in Loops
- **Pitfall**: Python closures bind variables by reference, not by value. When creating functions/lambdas inside a loop, all closures reference the final value of the loop variable.
- **Buggy Code**:
  ```python
  multipliers = [lambda x: x * i for i in range(4)]
  # Calling m(2) for any m yields 6 because i ends at 3!
  ```
- **Correction**: Bind default argument values at definition time:
  ```python
  multipliers = [lambda x, i=i: x * i for i in range(4)]
  ```

## 5. Swallowing Exceptions (`bare except:`)
- **Pitfall**: Using `except:` without specifying an exception class catches `KeyboardInterrupt`, `SystemExit`, and hides unexpected bugs like `NameError` or `TypeError`.
- **Correction**: Catch specific exceptions (`except (ValueError, KeyError) as e:`) and log or re-raise if unrecoverable.

## 6. Floating-Point Precision & Rounding Issues
- **Pitfall**: Standard IEEE-754 floats have precision limits: `0.1 + 0.2 != 0.3`.
- **Correction**: Use `math.isclose(a, b)` for floating point comparisons, or the `decimal.Decimal` module for monetary calculations.

