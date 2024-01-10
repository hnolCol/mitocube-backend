import string
import random 
import numpy as np

def get_random_string(N  : int = 20) -> str:
    """
    Returns a pseudo random string of N characters using upper, lowercases as well digits

    Parameters
    ----------
    N : int, default 20 
        The length of the pseudo-randomly created string 

    Returns 
    -------
    str 
        The pseudo random string. 
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k=N))

def get_random_number(min_value : int, max_value : int, size : int | tuple = 1) -> int:
    """
    Returns a random number/array of numbers between min_value and max_value of size (int or tuple)
    """
    rng = np.random.default_rng()
    return rng.integers(low=min_value, high=max_value, size=size)