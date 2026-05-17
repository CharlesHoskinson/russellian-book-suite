(ns bermuda.core
  "CLI entry. Dispatches: translate, verify, typeset."
  (:require [bermuda.phases :as p]
            [cljs.reader :as edn]
            ["fs" :as fs]))

(defn -read-edn [path]
  "Exposed for tests; treat as private."
  (edn/read-string (.toString (.readFileSync fs path))))

(defn -write-edn [path data]
  "Exposed for tests; treat as private."
  (.writeFileSync fs path (pr-str data)))

(defn main [& args]
  (let [[cmd in out] args]
    (case cmd
      "translate" (-write-edn out (p/translate (-read-edn in)))
      "verify"    (-write-edn out (p/verify    (-read-edn in)))
      "typeset"   (p/typeset in out)
      (do (println "usage: main.js <translate|verify|typeset> <in> <out>")
          (.exit js/process 2)))))
