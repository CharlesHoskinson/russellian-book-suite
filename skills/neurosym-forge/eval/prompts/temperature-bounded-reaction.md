# Prompt: temperature-bounded reaction verifier

Build a verifier for the chemical-reaction-temperature-bounds domain.
A reaction proceeds if the observed temperature `T` is in the closed
interval `[Tmin, Tmax]`. The book provides `Tmin`, `Tmax`, and the
observed `T` for each reaction; verify that every observed `T`
satisfies the bounds. Use the BookLogic DSL and the neurosym-forge
scaffold. Land at a passing `make ci`.
