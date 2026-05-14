import http from "k6/http";
import { check, sleep } from "k6";
import { Trend, Counter, Rate } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://103.173.99.217:8000";

const latency = new Trend("cpp_latency_ms", true);
const verdictAccepted = new Counter("verdict_accepted");
const verdictFailed = new Counter("verdict_failed");
const errorRate = new Rate("error_rate");

export const options = {
  scenarios: {
    burst: {
      executor: "constant-arrival-rate",
      rate: 10,
      timeUnit: "1s",
      duration: "20s",
      // Pre-allocate all 50 VUs upfront so no iteration is dropped waiting for a VU.
      preAllocatedVUs: 200,
      maxVUs: 250,
      gracefulStop: "3m",
    },
  },
  // Ask k6 to include p(50), p(95), p(99) in Trend summary data.
  summaryTrendStats: ["med", "p(95)", "p(99)", "max"],
  thresholds: {
    error_rate: ["rate<0.01"],
    http_req_failed: ["rate<0.01"],
    verdict_accepted: ["count>0"],
  },
};

const payload = JSON.stringify({
  language: "cpp",
  source_code:
    "vector<int> twoSum(vector<int> nums, int target) { unordered_map<int, int> mp; for (int i = 0; i < nums.size(); i++) { int complement = target - nums[i]; if (mp.count(complement)) { return {mp[complement], i}; } mp[nums[i]] = i; } return {}; }",
  function_name: "twoSum",
  test_cases: [
    { input: { nums: [2, 7, 11, 15], target: 9 }, expected_output: [0, 1] },
    { input: { nums: [3, 2, 4], target: 6 }, expected_output: [1, 2] },
    { input: { nums: [3, 3], target: 6 }, expected_output: [0, 1] },
  ],
});

const params = {
  headers: { "Content-Type": "application/json" },
  timeout: "360s",
};

export default function () {
  const start = Date.now();
  const res = http.post(`${BASE_URL}/execute`, payload, params);
  const duration = Date.now() - start;

  latency.add(duration);
  errorRate.add(res.status !== 200);

  const accepted = check(res, {
    "status 200": (r) => r.status === 200,
    "verdict accepted": (r) => {
      try {
        return JSON.parse(r.body).verdict === "accepted";
      } catch {
        return false;
      }
    },
  });

  if (accepted) {
    verdictAccepted.add(1);
  } else {
    verdictFailed.add(1);
    console.error(`status=${res.status} body=${res.body?.slice(0, 300)}`);
  }
}

export function handleSummary(data) {
  const m = data.metrics;
  const p50 = m.cpp_latency_ms?.values?.["med"]?.toFixed(0) ?? "N/A";
  const p95 = m.cpp_latency_ms?.values?.["p(95)"]?.toFixed(0) ?? "N/A";
  const p99 = m.cpp_latency_ms?.values?.["p(99)"]?.toFixed(0) ?? "N/A";
  const pMax = m.cpp_latency_ms?.values?.["max"]?.toFixed(0) ?? "N/A";
  const sent = m.http_reqs?.values?.count ?? 0;
  const accepted = m.verdict_accepted?.values?.count ?? 0;
  const failed = m.verdict_failed?.values?.count ?? 0;
  const errPct = ((m.error_rate?.values?.rate ?? 0) * 100).toFixed(1);
  const dropped = 50 - sent;

  const summary = `
========================================
  C++ twoSum — Burst Load Test
========================================
  Burst:              10 req/s × 5s = 50 requests
  Cooldown:           2 min (in-flight requests drain after burst)

  Throughput
  ─────────────────────────────────────
  Requests sent:      ${sent} / 50  (dropped by k6: ${dropped > 0 ? dropped : 0})
  Verdict accepted:   ${accepted}
  Verdict failed:     ${failed}
  Error rate:         ${errPct}%

  Latency (wall clock, incl. queue wait)
  ─────────────────────────────────────
  p50:                ${p50} ms
  p95:                ${p95} ms
  p99:                ${p99} ms
  max:                ${pMax} ms
========================================
`;

  console.log(summary);
  return { stdout: summary };
}
