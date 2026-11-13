"""
Sample 1: Buggy Logic & Runtime Traps
Contains:
1. Mutable default argument bug
2. Off-by-one indexing error in binary search
3. Division by zero on empty inputs / edge case
"""

def register_user_session(user_id, sessions=[]):
    # BUG: mutable default argument persists across requests
    sessions.append(user_id)
    return sessions


def binary_search(arr, target):
    left = 0
    right = len(arr)  # BUG: Should be len(arr) - 1 or carefully handled
    
    while left <= right:
        mid = (left + right) // 2
        # BUG: Off-by-one index error when right == len(arr)
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
            
    return -1


def compute_average_rating(ratings):
    # BUG: ZeroDivisionError if ratings list is empty
    total = sum(ratings)
    avg = total / len(ratings)
    return avg

