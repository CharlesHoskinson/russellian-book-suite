(ns bermuda.nl-to-fol-test
  "REQ-CLJS-ORCH-004, REQ-CLJS-ORCH-008: nl_to_fol module test."
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.nl-to-fol :as nl]))

(def opaque-claim
  {:id "C100"
   :source "x"
   :s {:kind :entity :name "X"}
   :p :unknown-predicate
   :o "raw string"
   :c []
   :modality :assertion
   :confidence 1.0})

(def quantity-claim
  {:id "C001"
   :source "bermuda-ch-02.md#L42"
   :s {:kind :entity :name "Bermuda"}
   :p :osmotic-pressure
   :o {:kind :quantity :value 1.5 :unit "atm"}
   :c []
   :modality :assertion
   :confidence 1.0})

(deftest opaque-claim-rewrites-to-opaque-symbol
  (testing "a claim that doesn't match the quantity shape falls through to ?other"
    (let [out (nl/claim->formula opaque-claim)]
      (is (= :OPAQUE (:name out)))
      (is (= :symbol (:kind out)))
      (is (= :formula (:sort out))))))

(deftest quantity-claim-rewrites-to-expression
  (testing "a quantity-shaped claim produces an :expression formula"
    (let [out (nl/claim->formula quantity-claim)]
      (is (= :expression (:kind out)))
      (is (= :formula (:sort out)))
      (is (map? (:head out)))
      (is (= :forall (get-in out [:head :name]))))))

(deftest to-si-atm
  (testing "atm → pascals conversion"
    (is (= 101325.0 (nl/to-si 1.0 "atm")))
    (is (= 202650.0 (nl/to-si 2.0 "atm")))))

(deftest to-si-celsius
  (testing "Celsius → Kelvin conversion"
    (is (= 273.15 (nl/to-si 0.0 "C")))
    (is (= 373.15 (nl/to-si 100.0 "C")))))

(deftest to-si-unknown-unit
  (testing "unknown unit returns the raw value"
    (is (= 42 (nl/to-si 42 "furlongs")))))

(deftest translate-corpus-maps-over-claims
  (testing "translate-corpus is mapv over claim->formula"
    (let [out (nl/translate-corpus [opaque-claim quantity-claim])]
      (is (= 2 (count out)))
      (is (= :OPAQUE (:name (first out))))
      (is (= :expression (:kind (second out)))))))
