### UnvibeCode — what this change did

**Business workflows:** not comparable — no workflow map was produced for the base run.

Detected in head (3), baseline unknown:
- Sign JWT claims
- JWT parsing, signature verification, and claims validation
- Extract and parse JWTs from HTTP requests

| | Base | Head | Δ (net) |
|---|---:|---:|---:|
| Files analysed | 44 | 43 | -1 |
| Symbols | 61 | 103 | +42 |
| Connections | 61 | 89 | +28 |

**Files added (1):**
- `jwt_test.go`

**Symbols added (51):**
- `map_claims_test.go::TestMapClaimsVerifyExpiresAtExpire (function)`
- `map_claims_test.go::TestMapClaims_GetAudience (function)`
- `map_claims_test.go::TestMapClaims_GetExpirationTime_StringIsInvalidType (function)`
- `map_claims_test.go::TestMapClaims_GetExpirationTime_ZeroIsExpired (function)`
- `map_claims_test.go::TestMapClaims_parseString (function)`
- `map_claims_test.go::TestMapclaimsVerifyExpiresAtInvalidTypeString (function)`
- `map_claims_test.go::TestMapclaimsVerifyIssuedAtInvalidTypeString (function)`
- `map_claims_test.go::TestMapclaimsVerifyNotBeforeInvalidTypeString (function)`
- `map_claims_test.go::TestVerifyAud (function)`
- `map_claims_test.go::jwt (package)`
- …and 41 more

**Files removed (2):**
- `errors_go1_20.go`
- `errors_go_other.go`

**Symbols removed (9):**
- `validator.go::newValidator (function)`
- `validator.go::validator (struct)`
- `validator.go::validator.Validate (method)`
- `validator.go::validator.verifyAudience (method)`
- `validator.go::validator.verifyExpiresAt (method)`
- `validator.go::validator.verifyIssuedAt (method)`
- `validator.go::validator.verifyIssuer (method)`
- `validator.go::validator.verifyNotBefore (method)`
- `validator.go::validator.verifySubject (method)`

**Connections:** 30 added, 2 removed.
- `ecdsa.go` --calls_symbol--> `errors.go` (`newError`)
- `ecdsa.go` --file_import--> `errors.go`
- `ed25519.go` --calls_symbol--> `errors.go` (`newError`)
- `ed25519.go` --file_import--> `errors.go`
- `errors_test.go` --calls_symbol--> `errors.go` (`newError`)

> **Analysis coverage was incomplete:**
> - *(head)* `risk findings` was not produced — state `DISABLED` (reason: DISABLED_BY_SERVER_POLICY).
> - *(head)* The run reports `overall_status: COMPLETE` despite the above, so a missing deliverable is not visible without reading this file.
> - *(base)* `business workflows` was not produced — state `UNAVAILABLE` (reason: UNAVAILABLE).
> - *(base)* `risk findings` was not produced — state `UNAVAILABLE` (reason: UNAVAILABLE).
> - *(base)* Lane `FULL_ANALYSIS` finished as `FAILED`.
>
> Treat the comparison above as partial — a deliverable missing from either run cannot be diffed.

<sub>unvibecode-watch · base `jwt-old-unvibecode-analysis-20261115_152237` → head `jwt-unvibecode-analysis-20261115_142850`</sub>
