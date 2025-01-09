import os
import sys
import time  # Unused import
import random  # Unused import
from math import sqrt, pi

def some_function(x, y):
    if x > y:   # Indentation Error: should be 4 spaces, not 2
      print("x is greater than y")
    elif x < y:
        print("y is greater than x")  # Correct indentation but inconsistent with above.
      return sqrt(x + y)  # Indentation issue here again.
    else:
        print("x and y are equal")

    # Line too long (more than 79 characters):
    print("This is a line that is way too long and should trigger a flake8 error because it exceeds the 79 characters limitation.")

def another_function(arg):
  return random.choice([arg, "default"])   # Trailing whitespace at the end

some_function(10, 5)

# Comment that is too long and would be flagged by flake8 for exceeding the line length limit, which should be 72 or 79 characters
# This comment is way too long for a normal style guide and should cause an error because it doesn't fit within the recommended length of the comment line.
print("This is an extra print statement that is not necessary and will cause an unused import warning.")

if __name__ == "__main__":
    another_function("test")
    sys.exit(0)  # sys.exit is unused here, so Flake8 will complain about it
