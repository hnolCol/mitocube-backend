

from enum import Enum 

class TimeUnitToSecondsEnum(Enum):
    s = 1
    min = 1 / 60 
    h = 1 / 60 / 60 
    d = 1 / 60 / 60 / 24
    w = 1 / 60 / 60 / 24 / 7 
    m = 1 / 60 / 60 / 24 / 30.44
    a = 1 / 60 / 60 / 24 / 365.25 


class PrefixEnum(Enum):
    "" 
    T : float = 10**12
    G : float = 10**9
    M : float = 10**6 
    k : float = 1000 
    NA : float = 1.0
    d : float = 1/ 10 
    c : float = 1 / 100
    m : float = 1 / 1000 
    µ : float = 10**-6 
    n : float = 10**-9 
    p : float = 10**-12 
    f : float = 10**-15
    