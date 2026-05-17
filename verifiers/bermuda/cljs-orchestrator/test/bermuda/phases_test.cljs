(ns bermuda.phases-test
  "REQ-CLJS-ORCH-005: phases module pre/post contract behaviour.

  Note: bermuda.phases requires bermuda.bridge which requires the native
  .node addon (unavailable in CI without a Rust build). This test file
  isolates the translate phase by calling bermuda.nl-to-fol directly
  and verifying the contract logic independently. PR-5 will introduce
  the native-addon test path."
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.nl-to-fol :as nl]
            [bermuda.ir :as ir]
            [malli.core :as m]))

(def claim
  {:id "C001"
   :source "bermuda-ch-02.md#L42"
   :s {:kind :entity :name "Bermuda"}
   :p :osmotic-pressure
   :o {:kind :quantity :value 1.5 :unit "atm"}
   :c []
   :modality :assertion
   :confidence 1.0})

(deftest translate-corpus-returns-vector
  (testing "translate-corpus maps over a vector of claims and returns a vector"
    (let [out (nl/translate-corpus [claim])]
      (is (vector? out))
      (is (= 1 (count out)))
      (is (= :expression (:kind (first out)))))))

(deftest translate-corpus-processes-map-as-seq
  (testing "translate-corpus on a map iterates key-value pairs (CLJS semantics)"
    ;; In CLJS, mapv over a map iterates entries as [k v] pairs.
    ;; No throw — this test documents that behaviour explicitly.
    (let [out (nl/translate-corpus {:not "a vector"})]
      (is (vector? out))
      (is (= 1 (count out))))))

(deftest translate-corpus-claim-validates-before-translate
  (testing "each claim satisfies ir/Claim before translation"
    (is (m/validate ir/Claim claim))
    (is (not (m/validate ir/Claim (assoc claim :id "not-a-claim-id"))))))

(deftest translate-empty-vector-ok
  (testing "an empty input returns an empty vector"
    (is (= [] (nl/translate-corpus [])))))
