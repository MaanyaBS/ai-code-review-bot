#!/usr/bin/env python3
"""
Test file for AI code review bot
This file contains some code that should trigger AI review comments
"""


def calculate_fibonacci(n):
    """
    Calculate the nth Fibonacci number

    Args:
        n (int): The position in the Fibonacci sequence

    Returns:
        int: The nth Fibonacci number
    """
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)


def main():
    """Main function to test Fibonacci calculation"""
    print("Testing Fibonacci calculation:")
    for i in range(10):
        result = calculate_fibonacci(i)
        print(f"Fibonacci({i}) = {result}")


if __name__ == "__main__":
    main()
