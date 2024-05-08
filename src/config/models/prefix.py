from pydantic import BaseModel

class PrefixModel(BaseModel):
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
    
