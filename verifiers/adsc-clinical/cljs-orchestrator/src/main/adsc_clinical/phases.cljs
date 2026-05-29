(ns adsc-clinical.phases
  "Phase driver with malli pre/post contracts."
  (:require [adsc-clinical.ir         :as ir]
            [adsc-clinical.nl-to-fol  :as t]
            [adsc-clinical.bridge     :as b]
            [malli.core                    :as m]
            ["fs" :as fs]))

(def MAX-REMEDIES 3)

(defn translate [claims]
  ;; CONTRACT DIVERGENCE (intentional): unlike the bermuda orchestrator, which
  ;; accepts [:vector ir/ClaimOrEvent] and dispatches trace events through
  ;; event->formula, this verifier accepts legacy Claim maps ONLY. Its
  ;; nl_to_fol has no event-trace dispatch — any 2-tuple event would fall
  ;; through to the :OPAQUE marker and carry no semantics — so the
  ;; precondition deliberately rejects event traces rather than silently
  ;; dropping them. Adding event support is a verifier-capability decision,
  ;; not a schema tweak; see ir.cljs (no Event/ClaimOrEvent schema by design).
  {:pre  (m/validate [:vector ir/Claim] claims)
   :post (m/validate [:vector ir/Formula] %)}
  (t/translate-corpus claims))

(defn verify [formulas]
  {:pre  (m/validate [:vector ir/Formula] formulas)
   :post (m/validate ir/Verdict %)}
  (b/verify-formulas (pr-str {:version 1 :atoms formulas})))

(defn typeset [report-path out-path]
  (b/render-pdf (.toString (.readFileSync fs report-path)) out-path))
