import numpy as np 
from lib.data.utils.base import squareSum, mean
from numba import jit 

@jit(nopython=True)
def pearson(p : np.ndarray, q : np.ndarray, nanp : np.ndarray = None, nanq : np.ndarray = None, reverse : bool = True, check_nan : bool = False) -> float:
    """
    Distance pearson implementation  (1-r). 
    """
    if check_nan and nanp is not None and nanq is not None:
        nan = nanp + nanq > 0   
        p = p[~nan]
        q = q[~nan]
    psize = p.size
    if p.size < 2: return 1.0 if reverse else 0
    pmean = mean(p)
    qmean = mean(q)
    
    SSP = squareSum(p,pmean)
    SSQ = squareSum(q,qmean)
    
    ri = 0
    for i in range(psize):
        ri+= (p[i]-pmean) * (q[i]-qmean)
    rd = (SSP * SSQ)**0.5
    r = ri / rd 
    if r > 1:
        r = 1.0 
    if reverse:
        return 1 - ri / rd 
    else:
        return ri / rd