(ns bermuda.booklogic-test
  "REQ-CLJS-ORCH: BookLogic predicates.edn codegen."
  (:require [cljs.test :refer-macros [deftest is]]
            [cljs.reader]
            [bermuda.booklogic :as bl]))

(deftest predicates-edn-parse-bool-value-kind
  ;; parse-bool lifts must type as :bool, not fall through to :string.
  (let [src      {:sorts      [(list 'defsort :entity)]
                  :predicates [(list 'defpredicate :primary-endpoint-met [:entity] :bool)]
                  :lifts      [(list 'deflift 'L005
                                     :from :claim/canonical-text
                                     :when "(?i)primary\\s+endpoint\\s+(?<v>met|missed)"
                                     :emit (list 'fact '?claim-id :t :primary-endpoint-met
                                                 (list 'parse-bool '?v)))]
                  :rules       []
                  :constraints []
                  :queries     []
                  :remedies    []}
        expanded (bl/expand src)
        text     (#'bermuda.booklogic/emit-predicates-edn-string expanded)]
    (is (re-find #":primary-endpoint-met" text))
    (is (re-find #":value-kind :bool" text))))

(deftest assert-form-approx-recognises-both-spellings
  ;; The approximate-equality recogniser must accept BOTH the `approx=`
  ;; spelling used in rules/booklogic/constraints.edn AND the `~=` alias.
  (let [approx? #'bermuda.booklogic/assert-form-approx?
        tol     #'bermuda.booklogic/extract-tolerance]
    (is (approx? (list 'approx= :lhs :rhs))
        "(approx= LHS RHS) must be recognised as approximate")
    (is (approx? (list '~= :lhs :rhs))
        "(~= LHS RHS) must be recognised as approximate")
    (is (= 0.03 (tol (list 'approx= :lhs :rhs :tolerance 0.03)))
        "tolerance must extract from an approx= form")
    (is (= 0.03 (tol (list '~= :lhs :rhs :tolerance 0.03)))
        "tolerance must extract from a ~= form")))

(deftest predicates-edn-merges-multiple-lifts-per-predicate
  ;; Two lifts targeting the same predicate accumulate their :patterns.
  (let [src      {:sorts      [(list 'defsort :entity)]
                  :predicates [(list 'defpredicate :parishes-count [:entity] :int)]
                  :lifts      [(list 'deflift 'L001
                                     :from :claim/canonical-text
                                     :when "(?i)(?<n>\\d+)\\s+parishes?"
                                     :emit (list 'fact '?claim-id :Bermuda :parishes-count
                                                 (list 'parse-int '?n)))
                               (list 'deflift 'L002
                                     :from :claim/canonical-text
                                     :when "(?i)(?<n>\\d+)\\s+civil\\s+parishes?"
                                     :emit (list 'fact '?claim-id :Bermuda :parishes-count
                                                 (list 'parse-int '?n)))]
                  :rules       []
                  :constraints []
                  :queries     []
                  :remedies    []}
        expanded (bl/expand src)
        text     (#'bermuda.booklogic/emit-predicates-edn-string expanded)
        parsed   (cljs.reader/read-string text)
        entry    (get-in parsed [:predicates :parishes-count])]
    (is (= 2 (count (:patterns entry)))
        "both lift patterns must be retained for the shared predicate")))
