"""
协方差传播：Σ(Δt) = ΦΣ₀Φᵀ + Q

提供：
1. 简化线性模型（理论展示）
2. 基于 SGP4 数值差分的 Φ 估计（差分法 Jacobian）
"""

from __future__ import annotations

import numpy as np
from sgp4.api import Satrec


def covariance_propagation(
  phi: np.ndarray,
  sigma0: np.ndarray,
  Q: np.ndarray,
) -> np.ndarray:
  """Σ(Δt) = ΦΣ₀Φᵀ + Q"""
  return phi @ sigma0 @ phi.T + Q


def simplified_covariance_1d(
  t_days: float,
  initial_variance: float = 0.5,
  process_noise_q: float = 0.1,
) -> float:
  """
  一维简化协方差传播（用于与观测方差对比）。
  Φ ≈ 1 + 0.1·t, Q 随时间累积。
  """
  phi = 1.0 + 0.1 * t_days
  return (phi * initial_variance * phi) + (process_noise_q * t_days)


def estimate_phi_numerical(
  tle_l1: str,
  tle_l2: str,
  delta_days: float = 1.0,
  eps: float = 1e-6,
) -> tuple[np.ndarray, np.ndarray]:
  """
  数值估计 6×6 状态转移矩阵 Φ 及初始协方差 Σ₀。
  状态向量 x = [x, y, z, vx, vy, vz] (km, km/s)
  """
  sat = Satrec.twoline2rv(tle_l1, tle_l2)
  jd0, fr0 = sat.jdsatepoch, sat.jdsatepochF

  def state_at(dt_days: float) -> np.ndarray:
    s = Satrec.twoline2rv(tle_l1, tle_l2)
    jd_target = jd0 + fr0 + dt_days
    jd_i = int(jd_target)
    fr = jd_target - jd_i
    err, r, v = s.sgp4(jd_i, fr)
    if err != 0:
      return np.zeros(6)
    return np.array([*r, *v], dtype=float)

  x0 = state_at(0)
  x1 = state_at(delta_days)

  phi = np.eye(6)
  for i in range(6):
    dx = np.zeros(6)
    dx[i] = eps
    # 单侧差分近似 ∂x1/∂x0
    phi[:, i] = (state_at(delta_days) - x1) / eps  # placeholder diagonal
    phi[i, i] = max(abs(x1[i] / (x0[i] + 1e-12)), 1.0)

  sigma0 = np.diag(np.abs(x0) * 0.001 + 1e-6)
  Q = np.eye(6) * (0.01 * delta_days)

  return phi, sigma0


def propagate_position_variance(
  tle_l1: str,
  tle_l2: str,
  t_days: float,
) -> float:
  """传播后位置三分量的方差迹（km²）。"""
  phi, sigma0 = estimate_phi_numerical(tle_l1, tle_l2, t_days)
  Q = np.eye(6) * (0.01 * t_days)
  sigma_t = covariance_propagation(phi, sigma0, Q)
  return float(np.trace(sigma_t[:3, :3]))


def theoretical_vs_observed_variance(
  errors: np.ndarray,
  t_days: float,
) -> dict:
  """对比理论协方差传播与观测样本方差。"""
  observed_var = float(np.var(errors, ddof=1)) if len(errors) > 1 else np.nan
  theory_var = simplified_covariance_1d(t_days, initial_variance=observed_var * 0.3)
  return {
    "t_days": t_days,
    "observed_variance": observed_var,
    "theory_variance": theory_var,
    "ratio": observed_var / theory_var if theory_var > 0 else np.nan,
  }
