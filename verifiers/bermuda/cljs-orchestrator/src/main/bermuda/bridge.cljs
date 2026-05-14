(ns bermuda.bridge
  "Calls into the native Rust addon built by napi-rs."
  (:require ["../native/bermuda-verifier.node" :as native]
            [cljs.reader :as edn]))

(defn verify-formulas [formulas-edn]
  (let [verdict-edn (native/verifyFormulas formulas-edn)]
    (edn/read-string verdict-edn)))

(defn saturate-equalities [terms-edn rules-edn]
  (edn/read-string (native/saturate terms-edn rules-edn)))

(defn render-pdf [latex-source out-path]
  (native/renderPdf latex-source out-path))
