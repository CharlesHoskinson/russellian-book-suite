# Before / After Examples

Ten paired transformations spanning common technical-writing failure modes. Use these as calibration when uncertain whether a passage is already compliant.

## 1 — Hedge removal

**Before:** The script might fail if the server is under heavy load.
**After:** The script fails when server CPU utilization exceeds 90 percent.

## 2 — Passive to active

**Before:** The configuration is loaded by the daemon at startup.
**After:** The daemon loads the configuration at startup.

## 3 — Adjective excision

**Before:** Our highly performant, extraordinarily reliable, enterprise-grade database engine.
**After:** The database engine handles 50,000 writes per second with 99.99 percent uptime.

## 4 — Conditional atomization

**Before:** Provided that authentication succeeds and rate limits are respected, and assuming the database is reachable, the request will be processed.
**After:**
1. Authentication succeeds.
2. Rate limits are respected.
3. The database is reachable.
4. THEN the request is processed.

## 5 — Code-as-illustration to code-as-proof

**Before:**
> Here is an example showing how to use the API:
> ```python
> client.fetch(id=42)
> ```
> As you can see, it is straightforward.

**After:**
> The `fetch` method retrieves a resource by primary key in O(log n).
> ```python
> client.fetch(id=42)
> ```
> The single positional argument forbids ambiguity between key types.

## 6 — Sideways drift removal

**Before:** Section 3 covers authentication. Authentication is interesting historically because early systems used plaintext passwords. Today we use OAuth2.
**After:** Section 3 covers authentication. The system uses OAuth2.

## 7 — Conversational closer removal

**Before:** I hope this helps you understand the architecture. Let me know if you have any questions!
**After:** *(deleted)*

## 8 — Nominalization to verb

**Before:** The implementation of the validation of the input is the responsibility of the parser.
**After:** The parser validates the input.

## 9 — Mixed list to parallel

**Before:**
- Install the package
- Configuration of the environment
- You should run the script
- Verification of outputs

**After:**
- Install the package.
- Configure the environment.
- Run the script.
- Verify the outputs.

## 10 — Speculation to threshold

**Before:** Performance is generally acceptable for most workloads.
**After:** P95 latency stays below 200ms for workloads under 10,000 requests per second.
