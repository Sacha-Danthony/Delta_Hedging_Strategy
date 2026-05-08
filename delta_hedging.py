import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

# ── Paramètres du projet ──────────────────────────────────────
S0          = 100      # Prix initial
K           = 100      # Strike ATM
r           = 0.02     # Taux sans risque
sigma       = 0.20     # Volatilité
T           = 1.0      # Maturité 1 an
days        = 21       # Jours de simulation
dt          = 1/252    # Pas de temps journalier
n_contracts = 100      # Nombre de contrats


# ── Fonction Black-Scholes ────────────────────────────────────
def bs_greeks(S, K, r, T, sigma):
    """Prix et Greeks d'un call européen (sans dividendes)"""
    if T <= 0:
        return {"price": max(S - K, 0), "delta": 1.0 if S > K else 0.0,
                "gamma": 0.0, "vega": 0.0}
    if sigma <= 0:
        return {"price": 0, "delta": 0, "gamma": 0, "vega": 0}

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    delta = norm.cdf(d1)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega  = S * np.sqrt(T) * norm.pdf(d1) / 100

    return {"price": round(price, 4), "delta": round(delta, 4),
            "gamma": round(gamma, 6), "vega": round(vega, 4)}


# ── Simulation du prix du stock ───────────────────────────────
def simulate_stock(S0, r, sigma, days, dt):
    """Simule un chemin de prix journaliers (GBM)"""
    S = np.zeros(days)
    S[0] = S0
    for t in range(1, days):
        Z = np.random.randn()
        S[t] = S[t-1] * np.exp((r - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z)
    return S


# ── Boucle de delta-hedging ───────────────────────────────────
def delta_hedge(S_path, K, r, sigma, T, dt, n_contracts):
    """Simule la stratégie de delta-hedging sur 21 jours"""

    days = len(S_path)

    option_values = np.zeros(days)
    deltas        = np.zeros(days)
    gammas        = np.zeros(days)
    vegas         = np.zeros(days)
    pnl           = np.zeros(days)

    # Jour 0 — initialisation
    T_remaining = T
    greeks = bs_greeks(S_path[0], K, r, T_remaining, sigma)
    option_values[0] = greeks["price"] * n_contracts
    deltas[0]        = greeks["delta"]
    gammas[0]        = greeks["gamma"]
    vegas[0]         = greeks["vega"]

    stock_position = -deltas[0] * n_contracts
    cash           = -stock_position * S_path[0]

    # Boucle journalière
    for t in range(1, days):
        T_remaining = T - t * dt

        greeks = bs_greeks(S_path[t], K, r, max(T_remaining, 0), sigma)
        option_values[t] = greeks["price"] * n_contracts
        deltas[t]        = greeks["delta"]
        gammas[t]        = greeks["gamma"]
        vegas[t]         = greeks["vega"]

        pnl[t] = (-(option_values[t] - option_values[t-1])
                  + stock_position * (S_path[t] - S_path[t-1])
                  + r * cash * dt)

        new_position   = -deltas[t] * n_contracts
        cash          += -(new_position - stock_position) * S_path[t]
        stock_position = new_position

    return option_values, deltas, gammas, vegas, pnl


# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":

    # Simulation
    np.random.seed(42)
    S_path = simulate_stock(S0, r, sigma, days, dt)
    print(f"Prix jour 1  : {S_path[0]:.2f}")
    print(f"Prix jour 21 : {S_path[-1]:.2f}")
    print(f"Prix min     : {S_path.min():.2f}")
    print(f"Prix max     : {S_path.max():.2f}")

    # Hedging
    option_values, deltas, gammas, vegas, pnl = delta_hedge(
        S_path, K, r, sigma, T, dt, n_contracts
    )

    print(f"\nPnL total    : ${pnl.sum():.2f}")
    print(f"PnL max jour : ${pnl.max():.2f}")
    print(f"PnL min jour : ${pnl.min():.2f}")

    # ── Graphiques ────────────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Delta-Hedging Strategy — Flow Equity Option", fontsize=14)

    axes[0,0].plot(S_path, color="blue", linewidth=2)
    axes[0,0].axhline(y=K, color="red", linestyle="--", label="Strike K=100")
    axes[0,0].set_title("Prix du stock simulé")
    axes[0,0].set_xlabel("Jours")
    axes[0,0].set_ylabel("Prix ($)")
    axes[0,0].legend()
    axes[0,0].grid(True)

    axes[0,1].plot(deltas, color="orange", linewidth=2)
    axes[0,1].set_title("Delta au fil du temps")
    axes[0,1].set_xlabel("Jours")
    axes[0,1].set_ylabel("Delta")
    axes[0,1].grid(True)

    axes[1,0].bar(range(days), pnl,
                  color=["green" if x >= 0 else "red" for x in pnl])
    axes[1,0].axhline(y=0, color="black", linewidth=0.8)
    axes[1,0].set_title("PnL journalier")
    axes[1,0].set_xlabel("Jours")
    axes[1,0].set_ylabel("PnL ($)")
    axes[1,0].grid(True)

    axes[1,1].plot(np.cumsum(pnl), color="purple", linewidth=2)
    axes[1,1].axhline(y=0, color="black", linestyle="--")
    axes[1,1].set_title(f"PnL cumulé (Total: ${pnl.sum():.2f})")
    axes[1,1].set_xlabel("Jours")
    axes[1,1].set_ylabel("PnL cumulé ($)")
    axes[1,1].grid(True)

    plt.tight_layout()
    plt.savefig("/Users/sacha/Desktop/delta_hedging_results.png", dpi=150)
    plt.show()
    print("\nGraphique sauvegardé sur le Bureau !")

    # ── Test robustesse ───────────────────────────────────────
    print("\n=== Test Robustesse ===")
    for vol in [0.10, 0.20, 0.40]:
        S_test = simulate_stock(S0, r, vol, days, dt)
        _, _, _, _, pnl_test = delta_hedge(S_test, K, r, vol, T, dt, n_contracts)
        print(f"σ={int(vol*100)}% → PnL total: ${pnl_test.sum():.2f} | "
              f"PnL std: ${pnl_test.std():.2f}")