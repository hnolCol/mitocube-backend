import numpy as np 
from scipy.stats import t

def t_to_p(ts, ns, alternative="two-sided"):
    ts = np.asarray(ts)
    ns = np.asarray(ns)

    df = ns - 2

    if alternative == "two-sided":
        p = 2 * t.sf(np.abs(ts), df)
    elif alternative == "greater":
        p = t.sf(ts, df)
    elif alternative == "smaller":
        p = t.cdf(ts, df)
    else:
        raise ValueError("alternative must be 'two-sided', 'greater', or 'smaller'")

    return p