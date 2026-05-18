# Prompt: parishes-aggregation verifier

Build a verifier that checks the sum of district populations equals
the total country population stated in the book. The book provides a
per-district population for each district of a country plus a
country-level total. The verifier MUST flag a violation when the sum
of per-district populations diverges from the stated country total
beyond the BookLogic relative-tolerance default. Use the neurosym-forge
scaffold and the BookLogic DSL; land at a passing `make ci`.
