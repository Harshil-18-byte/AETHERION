import numpy as np
import pandas as pd
from scipy.stats import norm

DAYS_IN_YEAR = 365.0

def calculate_greeks(df: pd.DataFrame, risk_free_rate: float = 0.05) -> pd.DataFrame:
    """
    Computes theoretical prices and Greeks for a DataFrame using Black-Scholes.
    Expects df to have columns:
      - 'spot_close' (float)
      - 'strike' (float)
      - 'days_to_expiry' (int/float)
      - 'iv_proxy' (float, in percentage scale like 20.0 for 20%)
      
    Returns the same DataFrame with new columns appended.
    """
    df = df.copy()

    # Inputs
    S = df['spot_close'].values
    K = df['strike'].values
    
    # Avoid zero DTE to prevent division by zero in d1/d2 denominator
    # If DTE is 0 and it's end of day, option value is intrinsic only.
    DTE = np.maximum(df['days_to_expiry'].values, 0.0001)
    T = DTE / DAYS_IN_YEAR
    
    r = risk_free_rate
    
    # IV proxy might be 0, avoid division by zero
    # Assume minimum 1% IV (0.01) to keep math stable
    sigma = np.maximum(df['iv_proxy'].values / 100.0, 0.01)
    
    # Calculate d1 and d2
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    # CDFs and PDFs
    N_d1 = norm.cdf(d1)
    N_d2 = norm.cdf(d2)
    N_neg_d1 = norm.cdf(-d1)
    N_neg_d2 = norm.cdf(-d2)
    pdf_d1 = norm.pdf(d1)

    # Theoretical Prices
    # Call: S * N(d1) - K * e^(-rT) * N(d2)
    # Put: K * e^(-rT) * N(-d2) - S * N(-d1)
    discount = np.exp(-r * T)
    theo_ce = S * N_d1 - K * discount * N_d2
    theo_pe = K * discount * N_neg_d2 - S * N_neg_d1

    # Greeks
    # Delta
    delta_ce = N_d1
    delta_pe = N_d1 - 1.0

    # Gamma (same for Call and Put)
    gamma = pdf_d1 / (S * sigma * np.sqrt(T))

    # Vega (same for Call and Put, usually expressed per 1% change so divided by 100)
    vega = (S * pdf_d1 * np.sqrt(T)) / 100.0

    # Theta (usually expressed per day so divided by 365)
    theta_ce = (- (S * pdf_d1 * sigma) / (2 * np.sqrt(T)) - r * K * discount * N_d2) / DAYS_IN_YEAR
    theta_pe = (- (S * pdf_d1 * sigma) / (2 * np.sqrt(T)) + r * K * discount * N_neg_d2) / DAYS_IN_YEAR
    
    # Rho (per 1% change)
    rho_ce = (K * T * discount * N_d2) / 100.0
    rho_pe = (-K * T * discount * N_neg_d2) / 100.0
    
    # Prevent infinite/nan
    def safe_nan(arr):
        return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)

    # Assign to dataframe
    df['bs_theo_ce'] = safe_nan(theo_ce)
    df['bs_theo_pe'] = safe_nan(theo_pe)
    df['bs_delta_ce'] = safe_nan(delta_ce)
    df['bs_delta_pe'] = safe_nan(delta_pe)
    df['bs_gamma'] = safe_nan(gamma)
    df['bs_vega'] = safe_nan(vega)
    df['bs_theta_ce'] = safe_nan(theta_ce)
    df['bs_theta_pe'] = safe_nan(theta_pe)
    df['bs_rho_ce'] = safe_nan(rho_ce)
    df['bs_rho_pe'] = safe_nan(rho_pe)

    return df
