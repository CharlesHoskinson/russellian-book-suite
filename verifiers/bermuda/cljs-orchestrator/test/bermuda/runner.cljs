(ns bermuda.runner
  "cljs.test entry. shadow-cljs :node-test build auto-discovers
   namespaces matching :ns-regexp \"-test$\"; this file exists so
   downstream consumers can require a single load target if needed."
  (:require [cljs.test :as t]
            [bermuda.unify-test]))

(defn -main [& _args]
  (t/run-tests 'bermuda.unify-test))
