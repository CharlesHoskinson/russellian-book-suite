# Prompt: species-binomial verifier

Build a verifier that confirms every claim about a species references
a valid genus + species binomial form: two words, the genus
capitalised, the species lowercase, and both italicised in the source.
The book provides one species claim per row, including the raw string
and an italic/non-italic flag per token. The verifier MUST emit a
violation for any species claim whose binomial fails the shape rule.
Use the neurosym-forge scaffold and the BookLogic DSL; land at a
passing `make ci`.
