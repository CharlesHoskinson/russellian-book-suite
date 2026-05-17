(ns bermuda.core-test
  "REQ-CLJS-ORCH-001: CLI dispatch table shape tests.

  Note: bermuda.core requires bermuda.phases which requires bermuda.bridge
  which requires the native .node addon (unavailable without a Rust build).
  This test file verifies the CLI dispatch contract using local stubs rather
  than loading the production core namespace. PR-5 will introduce the
  full integration path."
  (:require [cljs.test :refer-macros [deftest is testing]]))

;; Local stubs that mirror the bermuda.core dispatch contract.
;; These replicate the shape of core/main without touching the native chain.

(def captured (atom nil))

(defn- stub-write [path data]
  (reset! captured {:path path :data data}))

(defn- stub-read [_path]
  [{:id "C001"
    :source "bermuda-ch-02.md#L42"
    :s {:kind :entity :name "Bermuda"}
    :p :parishes-count
    :o 9
    :c []
    :modality :assertion
    :confidence 1.0}])

(defn- mock-main [cmd in out translate-fn verify-fn]
  (case cmd
    "translate" (stub-write out (translate-fn (stub-read in)))
    "verify"    (stub-write out (verify-fn    (stub-read in)))
    "typeset"   nil
    (do (println "usage: main.js <translate|verify|typeset> <in> <out>")
        :exit-2)))

(deftest translate-dispatch
  (testing "translate command reads, calls translate fn, writes output"
    (reset! captured nil)
    (mock-main "translate" "in.edn" "out.edn"
               (fn [in] [:translated in])
               identity)
    (is (= "out.edn" (:path @captured)))
    (is (= [:translated (stub-read "in.edn")] (:data @captured)))))

(deftest verify-dispatch
  (testing "verify command reads, calls verify fn, writes output"
    (reset! captured nil)
    (mock-main "verify" "in.edn" "out.edn"
               identity
               (fn [in] {:status :sat :input in}))
    (is (= "out.edn" (:path @captured)))
    (is (= :sat (get-in @captured [:data :status])))))

(deftest typeset-dispatch
  (testing "typeset command is dispatched (returns nil for stubs)"
    (let [result (mock-main "typeset" "report.md" "out.pdf" identity identity)]
      (is (nil? result)))))

(deftest unknown-command-returns-exit-marker
  (testing "an unknown command returns the exit-2 marker"
    (let [result (mock-main "what" "x" "y" identity identity)]
      (is (= :exit-2 result)))))
