from __future__ import annotations

from abc import abstractmethod
from typing import Type, Self, Dict

# from datetime import datetime, timedelta
# from typing import List, Dict, Self  # , Any
# from deprecated import deprecated

try:
    print("Start Something")
    raise Exception("Something is going wrong here intentionally!")
    print("You will never ever see me!")
finally:
    print("Finish something important!")

print("=====================================")
try:
    print("Start")
    raise Exception("Something!")
    print("You will not see me!  I / II")
except:
    print("Error Handling, and forward?")
    raise Exception("Something Else!")
    print("You will not see me! II / II")
finally:
    print("Can you see me?")

print("You should not see me!")
