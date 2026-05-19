(ns adsc-clinical.core
  "CLI entry. Dispatches: translate, verify, typeset."
  (:require [adsc-clinical.phases :as p]
            [cljs.reader :as edn]
            ["fs" :as fs]))

(defn- read-edn [path]
  (edn/read-string (.toString (.readFileSync fs path))))

(defn- write-edn [path data]
  (.writeFileSync fs path (pr-str data)))

(defn main [& args]
  (let [[cmd in out] args]
    (case cmd
      "translate" (write-edn out (p/translate (read-edn in)))
      "verify"    (write-edn out (p/verify    (read-edn in)))
      "typeset"   (p/typeset in out)
      (do (println "usage: main.js <translate|verify|typeset> <in> <out>")
          (.exit js/process 2)))))
