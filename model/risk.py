# Convert predicted delay distributions into connection risk
from scipy.stats import norm
import numpy as np

MINIMUM_CONNECTION_TIME = 15   # minutes to deplane and reach the next gate
DELAY_CORRELATION = 0.4        # inbound and outbound delays move together
N_SAMPLES = 10_000


def sample_from_quantiles(levels, values, n, uniform_draws=None):
    """Draw samples from a distribution described by a set of quantiles.

    Values are sorted to remove quantile crossing, and the tails beyond the
    outermost quantiles are extended linearly rather than clamped.
    """
    if uniform_draws is None:
        uniform_draws = np.random.uniform(0, 1, n)

    levels = np.asarray(levels, dtype=float)
    values = np.maximum.accumulate(np.asarray(values, dtype=float))

    low_slope = (values[1] - values[0]) / (levels[1] - levels[0])
    high_slope = (values[-1] - values[-2]) / (levels[-1] - levels[-2])

    extended_levels = np.concatenate([[0.0], levels, [1.0]])
    extended_values = np.concatenate([
        [values[0] - low_slope * levels[0]],
        values,
        [values[-1] + high_slope * (1.0 - levels[-1])],
    ])
    return np.interp(uniform_draws, extended_levels, extended_values)


def correlated_uniforms(n, rho):
    """Generate two correlated uniform samples via a Gaussian copula."""
    mean = [0, 0]
    cov = [[1, rho], [rho, 1]]
    normals = np.random.multivariate_normal(mean, cov, size=n)

    # Convert standard normals to uniforms using the normal CDF.
    return norm.cdf(normals[:, 0]), norm.cdf(normals[:, 1])


def connection_risk(
    arrival_quantiles,
    departure_quantiles,
    quantile_levels,
    scheduled_buffer,
    min_connection_time=MINIMUM_CONNECTION_TIME,
    correlation=DELAY_CORRELATION,
    n_samples=N_SAMPLES,
):
    """Probability that a passenger misses a connection.

    arrival_quantiles:   predicted arrival delays for the inbound flight
    departure_quantiles: predicted departure delays for the outbound flight
    quantile_levels:     the probability levels those values correspond to
    scheduled_buffer:    minutes between scheduled arrival and departure
    """
    u_arr, u_dep = correlated_uniforms(n_samples, correlation)

    arrival_delays = sample_from_quantiles(
        quantile_levels, arrival_quantiles, n_samples, u_arr
    )
    departure_delays = sample_from_quantiles(
        quantile_levels, departure_quantiles, n_samples, u_dep
    )

    # Time available = scheduled buffer, extended by any outbound delay,
    # reduced by the inbound's lateness.
    time_available = scheduled_buffer + departure_delays - arrival_delays
    missed = time_available < min_connection_time

    return {
        "miss_probability": float(missed.mean()),
        "median_time_available": float(np.median(time_available)),
        "p10_time_available": float(np.percentile(time_available, 10)),
        "p90_time_available": float(np.percentile(time_available, 90)),
    }

if __name__ == "__main__":
    levels = [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
    arrival = [-15, -8, 0, 15, 45, 75, 160]
    departure = [-5, -2, 3, 15, 40, 65, 150]

    print("buffer  miss_prob  median_time_left")
    for buffer in [30, 45, 60, 90, 120]:
        r = connection_risk(arrival, departure, levels, buffer)
        print(f"{buffer:>6}  {r['miss_probability']:>9.1%}  {r['median_time_available']:>12.1f}")

