# Atomspace EDN IR

Every phase boundary serialises through EDN. Records are MeTTa-style atoms.

## Four atom kinds

```clojure
;; Symbol — an identifier
{:kind :symbol :name :osmotic-pressure :sort (:fn [:solution] :real)}

;; Variable — bound by quantifier or match
{:kind :variable :name "?s" :sort :solution}

;; Grounded — host value or function
{:kind :grounded :name :z3-check-all
 :sort (:fn [:atom] :verdict)
 :grounded {:lib :z3 :fn "check_all" :napi true}}

;; Expression — parenthesised list
{:kind :expression :head <atom> :args [<atoms>] :doc "..." :id "R042"}
```

## Top-level shape

```clojure
{:version 1
 :sorts   [:int :real :bool :solution :formula :verdict :rule :atom ...]
 :rules   [<rule atoms>]   ;; in rules/*.edn
 :atoms   [<all other atoms>]
 :grounded [<grounded atoms>]   ;; in rules/grounded.edn
 :predicates {<map>}              ;; in rules/predicates.edn, optional
 :checksums {<file -> sha256>}  ;; in rules/.checksums.edn
}
```

## Enforced invariants

- Every atom has a `:sort` field. `lint_atomspace.py` fails on missing.
- Every sort referenced from an atom appears in `:sorts`. `lint_atomspace.py` flags unknowns.
- Every rule's `:rhs` free variables appear on the `:lhs`. `lint_atomspace.py` flags unbound.
- Every rule has a fixture test `tests/rules/test_<ID>.cljs`. `lint_rewrite_coverage.py` flags missing.
- `rules/*.edn` checksums match `.checksums.edn`. Manual edits are detected.
