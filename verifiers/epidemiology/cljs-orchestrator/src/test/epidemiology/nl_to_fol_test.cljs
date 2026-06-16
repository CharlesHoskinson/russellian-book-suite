(ns epidemiology.nl-to-fol-test
  "Flat-atom contract test (#138/#139): translate-corpus must emit the
   {:kind :expression :id :predicate :subject :value} shape that the Rust
   SMT path (smt.rs::bind_atoms) and the Python ingesters consume."
  (:require [cljs.test :refer-macros [deftest is testing run-tests]]
            [epidemiology.nl-to-fol :as nl]
            [epidemiology.ir :as ir]
            [malli.core :as m]))

(def quantity-claim
  {:id "C001"
   :source "ch-02.md#L42"
   :s {:kind :entity :name "Cohort"}
   :p :basic-reproduction-number
   :o {:kind :quantity :value 54 :unit "count"}
   :c []
   :modality :assertion
   :confidence 1.0})

(def opaque-claim
  {:id "C100"
   :source "x"
   :s {:kind :entity :name "X"}
   :p :unknown-predicate
   :o "raw string"
   :c []
   :modality :assertion
   :confidence 1.0})

(deftest to-si-atm
  (testing "atm -> pascals conversion is preserved"
    (is (= 101325.0 (nl/to-si 1.0 "atm")))))

(deftest quantity-claim-rewrites-to-flat-atom
  (testing "a quantity-shaped claim produces a FLAT :expression atom"
    (let [out (nl/claim->formula quantity-claim)]
      (is (= :expression (:kind out)))
      (is (string? (:id out)))
      (is (keyword? (:predicate out)))
      (is (keyword? (:subject out)))
      (is (some? (:value out)))
      ;; no nested expression tree
      (is (nil? (:head out)))
      (is (nil? (:args out)))
      ;; unitless value passes through to-si unchanged
      (is (= 54 (:value out))))))

(deftest flat-atom-validates-against-Formula
  (testing "the flat atom validates against the updated ir/Formula schema"
    (let [out (nl/claim->formula quantity-claim)]
      (is (m/validate ir/Formula out)
          (str "Formula validation failed: "
               (pr-str (m/explain ir/Formula out)))))))

(deftest opaque-claim-falls-through-to-symbol-marker
  (testing "a non-quantity claim becomes an opaque :symbol marker"
    (let [out (nl/claim->formula opaque-claim)]
      (is (= :symbol (:kind out)))
      (is (m/validate ir/Formula out)))))

(deftest translate-corpus-maps-over-claims
  (testing "translate-corpus returns a vector of flat atoms"
    (let [out (nl/translate-corpus [quantity-claim opaque-claim])]
      (is (vector? out))
      (is (= 2 (count out)))
      (is (= :expression (:kind (first out))))
      (is (= :symbol (:kind (second out)))))))

(deftest translate-contract-accepts-claims-rejects-events
  (testing "phases/translate's [:vector ir/Claim] :pre accepts legacy claims
            but rejects trace-event tuples (documented contract divergence
            from bermuda, which accepts ClaimOrEvent)"
    ;; a vector of legacy Claim maps satisfies the precondition
    (is (m/validate [:vector ir/Claim] [quantity-claim opaque-claim]))
    ;; a book-knowledge trace event is a [head payload] tuple, NOT a Claim,
    ;; so it must fail the precondition rather than be silently dropped.
    (let [event ['claim/verified {:claim/id "C001"}]]
      (is (not (m/validate ir/Claim event)))
      (is (not (m/validate [:vector ir/Claim] [event]))))))

(defn -main [& _]
  (let [{:keys [fail error]} (run-tests)]
    (when (or (pos? fail) (pos? error))
      (.exit js/process 1))))
