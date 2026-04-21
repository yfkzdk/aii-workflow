#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

def find_even_numbers(numbers):
    if not isinstance(numbers, list):
        raise TypeError("Input must be a list")
    even_numbers = [num for num in numbers if isinstance(num, int) and num % 2 == 0]
    return even_numbers

def find_even_numbers_in_range(start, end):
    if start > end:
        start, end = end, start
    even_numbers = [num for num in range(start, end + 1) if num % 2 == 0]
    return even_numbers

def filter_even_numbers(input_list):
    even_numbers = []
    non_even_items = []
    for item in input_list:
        if isinstance(item, int):
            if item % 2 == 0:
                even_numbers.append(item)
            else:
                non_even_items.append(item)
        else:
            non_even_items.append(item)
    return even_numbers, non_even_items

def is_even(number):
    return isinstance(number, int) and number % 2 == 0

def main():
    print("=== Finding Even Numbers ===\n")
    test_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    even_in_list = find_even_numbers(test_list)
    print(f"1. Even numbers in {test_list}: {even_in_list}")

    start, end = 10, 20
    even_in_range = find_even_numbers_in_range(start, end)
    print(f"2. Even numbers from {start} to {end}: {even_in_range}")

    mixed_list = [1, 2, 3, "hello", 4.5, 6, 7, "world", 8, 9, 10]
    evens, non_evens = filter_even_numbers(mixed_list)
    print(f"3. Even numbers in mixed list: {evens}")
    print(f"   Non-even/non-integer items: {non_evens}")

    test_numbers = [2, 3, 10, 15, 20, 21]
    print("\n4. Check if numbers are even:")
    for num in test_numbers:
        result = "Yes" if is_even(num) else "No"
        print(f"   {num}: {result}")

if __name__ == "__main__":
    main()