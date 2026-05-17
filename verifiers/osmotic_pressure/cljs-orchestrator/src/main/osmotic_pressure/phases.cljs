(ns osmotic-pressure.phases
  "Phase driver with malli pre/post contracts."
  (:require [osmotic-pressure.ir         :as ir]
            [osmotic-pressure.nl-to-fol  :as t]
            [osmotic-pressure.bridge     :as b]
            [malli.core                    :as m]
            ["fs" :as fs]))

(def MAX-REMEDIES 3)

(defn translate [claims]
  {:pre  (m/validate [:vector ir/Claim] claims)
   :post (m/validate [:vector ir/Formula] %)}
  (t/translate-corpus claims))

(defn verify [formulas]
  {:pre  (m/validate [:vector ir/Formula] formulas)
   :post (m/validate ir/Verdict %)}
  (b/verify-formulas (pr-str formulas)))

(defn typeset [report-path out-path]
  (b/render-pdf (.toString (.readFileSync fs report-path)) out-path))
