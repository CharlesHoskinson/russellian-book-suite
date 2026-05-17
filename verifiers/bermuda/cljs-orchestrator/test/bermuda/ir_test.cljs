(ns bermuda.ir-test
  "REQ-CLJS-ORCH-003: IR schema malli round-trips."
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.ir :as ir]
            [malli.core :as m]))

(deftest sort-keyword-valid
  (testing "a bare keyword is a valid Sort"
    (is (m/validate ir/Sort :real))
    (is (m/validate ir/Sort :entity))))

(deftest sort-fn-valid
  (testing "a :fn-shaped map is a valid Sort"
    (is (m/validate ir/Sort
                    {:kind :fn :args [:real :real] :ret :real}))))

(deftest sort-enum-valid
  (testing "an :enum-shaped map is a valid Sort"
    (is (m/validate ir/Sort
                    {:kind :enum :members [:sat :unsat :unknown]}))))

(deftest atom-symbol-valid
  (testing "a :symbol atom validates"
    (is (m/validate ir/Atom {:kind :symbol :sort :real}))))

(deftest atom-variable-valid
  (testing "a :variable atom validates"
    (is (m/validate ir/Atom {:kind :variable :sort :entity}))))

(deftest atom-unknown-kind-invalid
  (testing "an unrecognised :kind fails"
    (is (not (m/validate ir/Atom {:kind :nonsense :sort :real})))))

(deftest claim-valid
  (testing "a fully-populated claim validates"
    (is (m/validate ir/Claim
                    {:id "C001"
                     :source "bermuda-ch-02.md#L42"
                     :s {:kind :entity :name "Bermuda"}
                     :p :parishes-count
                     :o 9
                     :c []
                     :modality :assertion
                     :confidence 1.0}))))

(deftest claim-bad-id-invalid
  (testing "a malformed claim id (not C\\d{3,}) fails"
    (is (not (m/validate ir/Claim
                         {:id "X1"
                          :source "x"
                          :s {} :p :foo :o 1 :c []
                          :modality :assertion
                          :confidence 1.0})))))

(deftest verdict-sat-valid
  (testing "minimal :sat verdict validates"
    (is (m/validate ir/Verdict {:status :sat}))))

(deftest verdict-unsat-with-core-valid
  (testing ":unsat verdict with core list validates"
    (is (m/validate ir/Verdict
                    {:status :unsat :core ["C001" "C002"]}))))
