/* SPDX-License-Identifier: MIT
 * CyberPilot isolated public synthetic candidate, never an E2/vehicle runtime.
 * Frozen scalar canonical arithmetic, separately rounded binary64 operations.
 */
#include <stddef.h>
#include <stdint.h>
#include <float.h>
#include <math.h>
#include <fenv.h>
#include <xmmintrin.h>

_Static_assert(sizeof(double) == 8 && DBL_MANT_DIG == 53 && DBL_MAX_EXP == 1024,
               "IEEE binary64 required");

int cp_environment(void) {
  if (fegetround() != FE_TONEAREST || (_mm_getcsr() & ((1u << 15) | (1u << 6) | (3u << 13)))) return 5;
  volatile double tiny = 0x0.0000000000001p-1022;
  volatile double one = 1.0, half = 0.5, normal = 0x1p-1022;
  volatile double kept = tiny * one, sub = normal * half, zero = tiny * half;
  return (kept == tiny && sub == 0x0.8p-1022 && zero == 0.0) ? 0 : 5;
}

int cp_noop(void) { return 0; }

int cp_stage2(const double *x, size_t n, size_t p, const int64_t *indices,
              size_t k, const double *mean, const double *std,
              const double *beta, size_t output_n, double *output,
              double *trace, size_t trace_n) {
  if (!x || !indices || !mean || !std || !beta || !output) return 1;
  if (!(p == 5 || p == 13 || p == 33 || p == 93) || k == 0 || k > p || output_n != n) return 1;
  if (n > SIZE_MAX / p / sizeof(double) || n > SIZE_MAX / k / sizeof(double)) return 1;
  if ((trace && trace_n != n * k) || (!trace && trace_n != 0)) return 1;
  if (cp_environment()) return 5;
  for (size_t j = 0; j < k; ++j) {
    if (indices[j] < 0 || (uint64_t)indices[j] >= p || (j == 0 && indices[j] != 0) ||
        (j && indices[j] <= indices[j - 1])) return 2;
    size_t c = (size_t)indices[j];
    if (!isfinite(mean[c]) || !isfinite(std[c]) || !isfinite(beta[j]) || (j && !(std[c] > 0.0))) return 2;
  }
  for (size_t i = 0; i < n; ++i) {
    if (x[i * p] != 1.0) return 1;
    for (size_t c = 0; c < p; ++c) if (!isfinite(x[i * p + c])) return 1;
    volatile double acc = 0.0;
    for (size_t j = 0; j < k; ++j) {
      size_t c = (size_t)indices[j];
      volatile double normalized = 1.0;
      if (j != 0) {
        volatile double difference = x[i * p + c] - mean[c];
        normalized = difference / std[c];
        if (!isfinite(difference) || !isfinite(normalized)) return 3;
      }
      volatile double product = normalized * beta[j];
      acc = acc + product;
      if (!isfinite(product) || !isfinite(acc)) return 4;
      if (trace) trace[i * k + j] = normalized;
    }
    output[i] = acc;
  }
  return 0;
}
