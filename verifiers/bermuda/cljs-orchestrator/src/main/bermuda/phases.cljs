(ns bermuda.phases
  "Phase driver with malli pre/post contracts."
  (:require [bermuda.ir         :as ir]
            [bermuda.nl-to-fol  :as t]
            [bermuda.bridge     :as b]
            [malli.core                    :as m]
            ["fs" :as fs]))

(def MAX-REMEDIES 3)

(defn translate [items]
  {:pre  (m/validate [:vector ir/ClaimOrEvent] items)
   :post (m/validate [:vector ir/Formula] %)}
  (t/translate-corpus items))

(defn verify [formulas]
  {:pre  (m/validate [:vector ir/Formula] formulas)
   :post (m/validate ir/Verdict %)}
  (b/verify-formulas (pr-str {:version 1 :atoms formulas})))

(defn typeset [report-path out-path]
  (b/render-pdf (.toString (.readFileSync fs report-path)) out-path))
