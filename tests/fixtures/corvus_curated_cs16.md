# CS16 — MCP Internet Scan (Petrel Run 2) — Curated Findings

**Date:** 2026-07-20
**Corvus version:** 1.3.1

## Summary

| Metric | Value |
|--------|-------|
| Targets | 134 HTTP |
| GHSAs filed | 2 |

---

## True Positives

### F01 — GHSA-7rqv-4g54-hcxh — CRITICAL — glimind.com SSRF + Credential Exposure

**Service:** Glimind Oracle MCP (`glimind-oracle` v0.1.0, `https://glimind.com/mcp`)

**Finding:** SSRF via `watch_tool` — AWS IMDS confirmed.

**Impact:** Cloud credential theft.
**CWE:** CWE-918

---

### F02 — GHSA-j62x-hg79-www6 — HIGH — finvestai.top XSS Injection Reflection

**Service:** FinanceMCP (`FinanceMCP` v4.8.1, `https://finvestai.top/mcp`)

**Finding:** 4× XSS injection reflected in error messages.

**CWE:** CWE-79
