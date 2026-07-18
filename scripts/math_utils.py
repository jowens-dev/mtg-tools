#!/usr/bin/env python3
"""Mathematical utility functions for MTG deck analytics, including multivariate hypergeometric calculations."""

import math


def hypergeometric_pmf(N: int, n: int, K: int, x: int) -> float:
    """Calculate the probability of drawing exactly x successes of a pool size K
    in a sample size n from a population N.
    """
    if x < 0 or x > n or x > K or (n - x) > (N - K):
        return 0.0
    try:
        return (math.comb(K, x) * math.comb(N - K, n - x)) / math.comb(N, n)
    except ZeroDivisionError:
        return 0.0


def hypergeometric_cdf_ge(N: int, n: int, K: int, k: int) -> float:
    """Calculate P(X >= k) for a hypergeometric distribution."""
    prob = 0.0
    for x in range(k, min(n, K) + 1):
        prob += hypergeometric_pmf(N, n, K, x)
    return prob


def calculate_joint_consistency(
    N: int,
    n: int,
    K_lands: int,
    k_lands: int,
    K_ramp: int,
    k_ramp: int,
    K_draw: int,
    k_draw: int
) -> float:
    """Calculate the exact joint probability of drawing >= k_lands, >= k_ramp, and >= k_draw
    in a hand of size n from a deck of size N using the multivariate hypergeometric distribution.
    """
    total_prob = 0.0
    K_other = N - (K_lands + K_ramp + K_draw)
    
    # Iterate over all possible combinations of draws for Lands, Ramp, and Draw
    # such that lands >= k_lands, ramp >= k_ramp, draw >= k_draw, and total <= n
    for x_lands in range(k_lands, min(n, K_lands) + 1):
        for x_ramp in range(k_ramp, min(n - x_lands, K_ramp) + 1):
            for x_draw in range(k_draw, min(n - x_lands - x_ramp, K_draw) + 1):
                x_other = n - (x_lands + x_ramp + x_draw)
                if x_other < 0 or x_other > K_other:
                    continue
                
                # Multivariate hypergeometric term
                try:
                    num = (math.comb(K_lands, x_lands) * 
                           math.comb(K_ramp, x_ramp) * 
                           math.comb(K_draw, x_draw) * 
                           math.comb(K_other, x_other))
                    den = math.comb(N, n)
                    total_prob += num / den
                except ZeroDivisionError:
                    pass
                    
    return total_prob
