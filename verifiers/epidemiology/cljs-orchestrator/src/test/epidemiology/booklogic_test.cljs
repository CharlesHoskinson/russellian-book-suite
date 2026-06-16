(ns epidemiology.booklogic-test
  "Live nbb test fixture for the BookLogic compiler.
   Invoked by the Python integration harness via nbb."
  (:require [cljs.test :refer-macros [deftest is run-tests]]
            [cljs.reader]
            [epidemiology.booklogic :as bl]
            ["fs" :as fs]
            ["path" :as path]))

(deftest expand-three-forms
  (let [src      {:sorts      [(list 'defsort :entity)
                               (list 'defsort :int)]
                  :predicates [(list 'defpredicate :parishes-count [:entity] :int)]
                  :lifts      [(list 'deflift 'L001
                                     :from :claim/canonical-text
                                     :when "(?i)(?<n>\\d+)\\s+parishes?"
                                     :emit (list 'fact '?claim-id :Bermuda :parishes-count
                                                 (list 'parse-int '?n)))]
                  :rules       []
                  :constraints []
                  :queries     []
                  :remedies    []}
        expanded (bl/expand src)]
    (is (= 2 (count (:sort-registry expanded))))
    (is (= 1 (count (:predicate-registry expanded))))
    (is (= 1 (count (:lift-rules expanded))))
    (is (= :parishes-count (-> expanded :predicate-registry first :name)))))

(deftest predicates-edn-shape
  (let [src      {:sorts      [(list 'defsort :entity)]
                  :predicates [(list 'defpredicate :parishes-count [:entity] :int)]
                  :lifts      [(list 'deflift 'L001
                                     :from :claim/canonical-text
                                     :when "(?i)(?<n>\\d+)\\s+parishes?"
                                     :emit (list 'fact '?claim-id :Bermuda :parishes-count
                                                 (list 'parse-int '?n))
                                     :word-to-int {"nine" 9})]
                  :rules       []
                  :constraints []
                  :queries     []
                  :remedies    []}
        expanded (bl/expand src)
        text     (#'epidemiology.booklogic/emit-predicates-edn-string expanded)]
    (is (re-find #":parishes-count" text))
    (is (re-find #":value-kind :int" text))
    (is (re-find #"\"nine\" 9" text))))

(deftest predicates-edn-merges-multiple-lifts-per-predicate
  ;; Two lifts targeting the same predicate must accumulate their :patterns
  ;; rather than the last lift overwriting the first.
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
        text     (#'epidemiology.booklogic/emit-predicates-edn-string expanded)
        parsed   (cljs.reader/read-string text)
        entry    (get-in parsed [:predicates :parishes-count])]
    (is (= 2 (count (:patterns entry)))
        "both lift patterns must be retained for the shared predicate")))

(deftest expand-defrule-basic
  (let [src      {:sorts      []
                  :predicates []
                  :lifts      []
                  :rules      [(list 'defrule 'R001-normalize-st-davids
                                     (list '= (list 'entity "St. David's Island")
                                              :St_Davids_Island)
                                     :tags [:normalization :entity])]
                  :constraints []
                  :queries     []
                  :remedies    []}
        expanded (bl/expand src)]
    (is (= 1 (count (:rewrite-rules expanded))))
    (let [rule (first (:rewrite-rules expanded))]
      (is (= 'R001-normalize-st-davids (:name rule)))
      (is (= [:normalization :entity]   (:tags rule)))
      (is (some? (:lhs rule)))
      (is (some? (:rhs rule))))))

(deftest expand-defrule-missing-equation-throws
  (is (thrown-with-msg?
        js/Error #"defrule.*must contain.*equation"
        (bl/expand {:sorts [] :predicates [] :lifts []
                    :rules [(list 'defrule 'R002 :tags [:foo])]
                    :constraints [] :queries [] :remedies []}))))

(deftest expand-defconstraint-basic
  (let [src      {:sorts [] :predicates [] :lifts [] :rules []
                  :constraints
                    [(list 'defconstraint 'C001-bermuda-parishes
                           :backend :z3
                           :assert (list '= (list :parishes-count :Bermuda) 9)
                           :track :claim/id
                           :on-unsat {:defect :D13
                                      :severity :critical
                                      :message "Claim contradicts canonical Bermuda parish count."})]
                  :queries [] :remedies []}
        expanded (bl/expand src)]
    (is (= 1 (count (:constraint-decls expanded))))
    (let [c (first (:constraint-decls expanded))]
      (is (= 'C001-bermuda-parishes (:name c)))
      (is (= :z3                    (:backend c)))
      (is (= :claim/id              (:track c)))
      (is (= :D13                   (-> c :on-unsat :defect)))
      (is (= :critical              (-> c :on-unsat :severity))))))

(deftest expand-defconstraint-approx-equality
  (let [src      {:sorts [] :predicates [] :lifts [] :rules []
                  :constraints
                    [(list 'defconstraint 'C002-vant-hoff
                           :backend :z3
                           :assert (list '~= (list :osmotic-pressure-pa :sample)
                                            (list '* (list :vant-hoff-i :sample) 8.314)
                                            :tolerance 0.03)
                           :on-unsat {:defect :D13 :severity :critical
                                      :message "van 't Hoff violated"})]
                  :queries [] :remedies []}
        expanded (bl/expand src)]
    (let [c (first (:constraint-decls expanded))]
      (is (= 'C002-vant-hoff (:name c)))
      (is (= '~=             (first (:assert c))))
      (is (= 0.03            (:tolerance c))))))

(deftest assert-form-approx-recognises-both-spellings
  ;; The approximate-equality recogniser must accept BOTH the `approx=`
  ;; spelling used in rules/booklogic/constraints.edn AND the `~=` alias.
  (let [approx? #'epidemiology.booklogic/assert-form-approx?
        tol     #'epidemiology.booklogic/extract-tolerance]
    (is (approx? (list 'approx= :lhs :rhs))
        "(approx= LHS RHS) must be recognised as approximate")
    (is (approx? (list '~= :lhs :rhs))
        "(~= LHS RHS) must be recognised as approximate")
    (is (= 0.03 (tol (list 'approx= :lhs :rhs :tolerance 0.03)))
        "tolerance must extract from an approx= form")
    (is (= 0.03 (tol (list '~= :lhs :rhs :tolerance 0.03)))
        "tolerance must extract from a ~= form")))

(deftest expand-defconstraint-missing-backend-throws
  (is (thrown-with-msg?
        js/Error #"defconstraint.*:backend"
        (bl/expand {:sorts [] :predicates [] :lifts [] :rules []
                    :constraints [(list 'defconstraint 'CX
                                        :assert (list '= 1 1)
                                        :on-unsat {:defect :D13 :severity :critical
                                                   :message "x"})]
                    :queries [] :remedies []}))))

(deftest expand-defquery-basic
  (let [src      {:sorts [] :predicates [] :lifts [] :rules [] :constraints []
                  :queries
                    [(list 'defquery 'Q001-low-confidence-load-bearing
                           :backend :cozo
                           :find [(list 'claim)]
                           :where [(list 'claim/load-bearing (list 'claim) true)
                                   (list 'claim/posterior   (list 'claim) (list 'p))
                                   (list '<  (list 'p) 0.80)]
                           :on-result {:defect :posterior-floor
                                       :severity :warning})]
                  :remedies []}
        expanded (bl/expand src)]
    (is (= 1 (count (:query-decls expanded))))
    (let [q (first (:query-decls expanded))]
      (is (= 'Q001-low-confidence-load-bearing (:name q)))
      (is (= :cozo                              (:backend q)))
      (is (= :posterior-floor (-> q :on-result :defect))))))

(deftest expand-defquery-missing-where-throws
  (is (thrown-with-msg?
        js/Error #"defquery.*:where"
        (bl/expand {:sorts [] :predicates [] :lifts [] :rules [] :constraints []
                    :queries [(list 'defquery 'QX
                                    :backend :cozo
                                    :find [(list 'x)]
                                    :on-result {:defect :x :severity :warning})]
                    :remedies []}))))

(deftest expand-defremedy-basic
  (let [src      {:sorts [] :predicates [] :lifts [] :rules []
                  :constraints [] :queries []
                  :remedies
                    [(list 'defremedy 'W001-unsat-core-to-refutation
                           :when (list 'unsat-core '?claim)
                           :propose (list 'ledger/transition '?claim :refuted)
                           :requires :human-review)]}
        expanded (bl/expand src)]
    (is (= 1 (count (:remedy-decls expanded))))
    (let [r (first (:remedy-decls expanded))]
      (is (= 'W001-unsat-core-to-refutation (:name r)))
      (is (= :human-review                   (:requires r)))
      (is (some? (:when r)))
      (is (some? (:propose r))))))

(deftest expand-defremedy-no-requires-defaults-to-auto-apply
  (let [src      {:sorts [] :predicates [] :lifts [] :rules []
                  :constraints [] :queries []
                  :remedies
                    [(list 'defremedy 'W002-low-conf-disputed
                           :when (list 'low-confidence '?claim)
                           :propose (list 'ledger/transition '?claim :disputed))]}
        expanded (bl/expand src)]
    (let [r (first (:remedy-decls expanded))]
      (is (= :auto-apply (:requires r))))))

(deftest canonical-var-name-matches-golden
  ;; REQ-EDN-045: CLJS canonical-var-name agrees with the cross-language
  ;; golden vectors at skills/neurosym-forge/tests/golden/canonical_var_name.edn.
  ;; The path is computed relative to the test cwd: nbb tests are invoked
  ;; from the project root, and the goldens live in the parent skill tree.
  (let [golden-path "../../skills/neurosym-forge/tests/golden/canonical_var_name.edn"]
    (when (.existsSync fs golden-path)
      (let [rows (cljs.reader/read-string
                  (.toString (.readFileSync fs golden-path)))]
        (doseq [{:keys [predicate subject want]} rows]
          (let [pred-in (if (keyword? predicate) (name predicate) predicate)
                subj-in (if (keyword? subject)   (name subject)   subject)
                got (bl/canonical-var-name pred-in subj-in)]
            (is (= got want)
                (str "(" (pr-str predicate) ", " (pr-str subject)
                     ") -> " got " (expected " want ")"))))))))

(defn -main [& _]
  (let [{:keys [fail error]} (run-tests)]
    (when (or (pos? fail) (pos? error))
      (.exit js/process 1))))
