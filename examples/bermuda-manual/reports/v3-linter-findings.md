# v3 Linter Findings - Bermuda Manual

Date: 2026-05-10  
Skill family: russellian-book-forge v3 (russellian-style + book-knowledge + book-compose + book-review)

## Per-chapter metrics

| Chapter | Passes | listicle | rhythm | hedge | passive | mod | citation | ai |
|---|---|---|---|---|---|---|---|---|
| ch-01 | False | 2 | 1 | 0 | 0.013 | 0 | 0 | 0 |
| ch-02 | False | 0 | 7 | 0 | 0.0 | 0 | 0 | 0 |
| ch-03 | False | 0 | 5 | 0 | 0.0 | 0 | 0 | 0 |
| ch-04 | False | 0 | 10 | 0 | 0.011 | 0 | 0 | 0 |
| ch-05 | False | 0 | 3 | 0 | 0.0 | 0 | 0 | 0 |
| ch-06 | False | 0 | 3 | 0 | 0.0 | 0 | 0 | 3 |
| ch-07 | False | 0 | 2 | 0 | 0.012 | 0 | 0 | 0 |
| ch-08 | False | 0 | 2 | 0 | 0.0 | 0 | 0 | 0 |
| ch-09 | False | 0 | 1 | 0 | 0.0 | 0 | 0 | 1 |
| ch-10 | False | 0 | 3 | 0 | 0.026 | 0 | 0 | 0 |

## Failed acceptance tests per chapter

### ch-01
- listicle_abstract_count == 0
- rhythm_violations == 0
- persona_reviews_complete == True

### ch-02
- rhythm_violations == 0
- persona_reviews_complete == True

### ch-03
- rhythm_violations == 0
- persona_reviews_complete == True

### ch-04
- rhythm_violations == 0
- persona_reviews_complete == True

### ch-05
- rhythm_violations == 0
- persona_reviews_complete == True

### ch-06
- rhythm_violations == 0
- persona_reviews_complete == True

### ch-07
- rhythm_violations == 0
- persona_reviews_complete == True

### ch-08
- rhythm_violations == 0
- persona_reviews_complete == True

### ch-09
- rhythm_violations == 0
- persona_reviews_complete == True

### ch-10
- rhythm_violations == 0
- persona_reviews_complete == True


## Summary

- Total listicle findings: 2 (in 1 chapters: ['ch-01'])
- Total rhythm violations: 37 (in 10 chapters)
- Total AI fingerprint findings: 4 (in 2 chapters: ['ch-06', 'ch-09'])

- Chapters needing revision (linter-only): all 10 (rhythm violations everywhere; ch-01 also has listicle)
- persona_reviews_complete failure: expected; persona reviews will run in Phase R3.