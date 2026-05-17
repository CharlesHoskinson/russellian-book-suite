(ns bermuda.nl-to-fol-test
  "REQ-CLJS-ORCH-004, REQ-CLJS-ORCH-008: nl_to_fol module test."
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.nl-to-fol :as nl]
            [bermuda.ir :as ir]
            [malli.core :as m]))

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
      (is (= :symbol (:kind out)))
      (is (= :formula (:sort out))))))

(deftest quantity-claim-rewrites-to-expression
  (testing "a quantity-shaped claim produces an :expression formula"
    (let [out (nl/claim->formula quantity-claim)]
      (is (= :expression (:kind out)))
      (is (= :formula (:sort out)))
      (is (map? (:head out)))
      (is (= :symbol (get-in out [:head :kind])))
      (is (= :rule (get-in out [:head :sort]))))))

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
      (is (= :symbol (:kind (first out))))
      (is (= :expression (:kind (second out)))))))

(deftest quantity-claim-output-validates-against-Formula
  (testing "REQ-CLJS-ORCH-008: claim->formula quantity-branch output is a valid ir/Formula"
    (let [out (nl/claim->formula quantity-claim)]
      (is (m/validate ir/Formula out)
          (str "Formula validation failed: "
               (pr-str (m/explain ir/Formula out)))))))

(deftest opaque-claim-output-validates-against-Formula
  (testing "REQ-CLJS-ORCH-008: claim->formula ?other branch output is also a valid ir/Formula"
    (let [out (nl/claim->formula opaque-claim)]
      (is (m/validate ir/Formula out)
          (str "Formula validation failed: "
               (pr-str (m/explain ir/Formula out)))))))

;;; ----- Event-stream dispatch (REQ-CLJS-ORCH-010, REQ-CLJS-ORCH-011) -----

(deftest claim-verified-event-produces-formula
  (testing "REQ-CLJS-ORCH-010: claim/verified event -> :expression formula"
    (let [event [(symbol "claim" "verified")
                 {:claim/id "clm-2026-000001"
                  :text     "Bermuda has nine traditional parishes."
                  :from     :proposed
                  :to       :verified}]
          out (nl/claim->formula event)]
      (is (some? out))
      (is (= :expression (:kind out))
          "verified events project to an :expression formula")
      (is (= :formula (:sort out))))))

(deftest source-ingested-event-skipped
  (testing "REQ-CLJS-ORCH-010: source/ingested produces nil — caller drops nils"
    (let [event [(symbol "source" "ingested")
                 {:doc/id "alpha" :kind :pdf}]
          out (nl/claim->formula event)]
      (is (nil? out)
          "source/ingested produces no formula — caller drops nils"))))

(deftest claim-proposed-event-skipped
  (testing "REQ-CLJS-ORCH-010: claim/proposed alone does not feed verification"
    (let [event [(symbol "claim" "proposed")
                 {:claim/id "clm-x" :text "candidate"}]
          out (nl/claim->formula event)]
      (is (nil? out)
          "claim/proposed alone does not feed verification"))))

(deftest atom-emitted-event-passes-through
  (testing "REQ-CLJS-ORCH-011: atom/emitted hands pre-compiled atom straight back"
    (let [emitted {:kind :symbol :sort :formula :name :PRE-COMPILED}
          event [(symbol "atom" "emitted") {:atom emitted}]
          out   (nl/claim->formula event)]
      (is (= emitted out)
          "atom/emitted hands the pre-compiled atom straight back"))))

(deftest unknown-event-head-emits-opaque
  (testing "REQ-CLJS-ORCH-011: unknown heads fall through to :OPAQUE marker"
    (let [event [(symbol "weather" "rained") {:mm 12}]
          out (nl/claim->formula event)]
      (is (= :OPAQUE (:name out))
          "unknown heads fall through to the :OPAQUE marker, matching
           the legacy ?other branch"))))

(deftest translate-corpus-mixes-claims-and-events-and-drops-nils
  (testing "REQ-CLJS-ORCH-010: nil-producing events are dropped from corpus"
    (let [ingested-ev  [(symbol "source" "ingested") {:doc/id "alpha"}]
          verified-ev  [(symbol "claim" "verified")
                        {:claim/id "clm-X" :text "x"
                         :from :proposed :to :verified}]
          out (nl/translate-corpus [opaque-claim ingested-ev verified-ev])]
      (is (= 2 (count out))
          "nil-producing events are dropped; both surviving entries are formulas")
      (is (every? #(= :expression (:kind %)) (filter #(= :expression (:kind %)) out))))))
