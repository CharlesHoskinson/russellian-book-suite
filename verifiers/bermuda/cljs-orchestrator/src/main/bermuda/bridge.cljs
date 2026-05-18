(ns bermuda.bridge
  "Calls into the native Rust addon built by napi-rs."
  (:require [cljs.reader :as edn]))

(def ^:private native (js/require "../native/bermuda-verifier.node"))

(defn verify-formulas [formulas-edn]
  (let [verdict-edn (.verifyFormulas native formulas-edn)]
    (edn/read-string verdict-edn)))

(defn saturate-equalities [terms-edn rules-edn]
  (edn/read-string (.saturate native terms-edn rules-edn)))

(defn render-pdf [latex-source out-path]
  (.renderPdf native latex-source out-path))
