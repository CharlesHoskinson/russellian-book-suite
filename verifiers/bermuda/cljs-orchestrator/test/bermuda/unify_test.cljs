(ns bermuda.unify-test
  "REQ-CLJS-ORCH-006: unify module test."
  (:require [cljs.test :refer-macros [deftest is testing]]
            [bermuda.unify :as u]))

(deftest unify-equal-keywords
  (testing "two equal keywords unify and return a single binding"
    (let [out (u/unify-atoms :a :a)]
      (is (seq out) "expected at least one solution")
      (is (= [:a :a] (first out))))))

(deftest unify-unequal-keywords
  (testing "two unequal keywords have no solutions"
    (is (empty? (u/unify-atoms :a :b)))))

(deftest unify-equal-maps
  (testing "structurally equal maps unify"
    (let [out (u/unify-atoms {:k 1} {:k 1})]
      (is (seq out))
      (is (= [{:k 1} {:k 1}] (first out))))))
