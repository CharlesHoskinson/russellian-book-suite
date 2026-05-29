(ns _induction-grammar
  "REQ-INDUCE-040..046: BookLogic grammar enforcer for the Tier 6
   theory-induction layer.

   The LLM proposer emits candidate EDN forms in response to a focused
   atom cluster plus the schema BNF. This module is the FIRST gate
   before any solver invocation; rejected proposals never reach Z3,
   Cozo, or egg. The deep-research reports converged on a single
   discipline: the LLM never invents the language. Everything outside
   this grammar is rejected here.

   Six disjoint failure categories, each tagged for the orchestrator's
   failure log:

     :grammar-fail/non-edn             — reader error / not parseable EDN
     :grammar-fail/wrong-head          — head is not `defconstraint`
     :grammar-fail/unknown-predicate   — predicate not in schema
     :grammar-fail/wrong-sort          — arg sort mismatch (reserved
                                         for V-Wave; full sort-checking
                                         lands when Phase W wires the
                                         schema's per-arg sort table)
     :grammar-fail/illegal-op          — op outside SUPPORTED-OPERATORS
     :grammar-fail/circular-definition — :assert references the rule's
                                         own :on-unsat defect id, so it
                                         proves itself without touching
                                         the atomspace (REQ-TEST-042)

   Public surface:

     (grammar-conforming? form schema)
         → {:ok true} | {:ok false :tag <kw> :reason <str>}

     (grammar-conforming-json form-str schema-str)
         → JSON string, suitable for Python test harnesses; the JSON
           keys are lower-case strings (`ok`, `tag`, `reason`)."
  (:require [cljs.reader :as edn]
            [clojure.set :as cset]
            [clojure.string :as str]))


(def ^:const SUPPORTED-OPERATORS
  "REQ-INDUCE-046: must stay in sync with codegen_axioms.py's
   `_SUPPORTED_ASSERT_HEADS`. The drift lint
   (`tests/test_induction_grammar_drift.py`) parses this set
   statically — keep the literal a single set of bare symbols on a
   single block so the regex in the lint stays simple."
  #{'= '~= 'approx=
    '< '<= '> '>=
    '+ '- '* '/
    'and 'or 'not '=> 'ite
    'sum 'count 'in 'select
    'forall 'exists})


;; ----- helpers --------------------------------------------------------------


(defn- predicate-call?
  "A predicate call inside `:assert` is `(:pred-name arg ...)` —
   sequential, first element is a keyword."
  [form]
  (and (sequential? form)
       (keyword? (first form))))


(defn- operator-call?
  "An operator call is `(op arg ...)` with `op` a symbol."
  [form]
  (and (sequential? form) (symbol? (first form))))


(defn- collect-predicates
  "Walk an `:assert` body collecting every predicate keyword in head
   position of a predicate-call sub-form."
  [form]
  (cond
    (predicate-call? form)
    (into #{(first form)}
          (mapcat collect-predicates (rest form)))

    (sequential? form)
    (into #{} (mapcat collect-predicates form))

    :else #{}))


(defn- collect-operators
  "Walk an `:assert` body collecting every op symbol in head position
   of an operator-call sub-form. Predicate-call sub-forms are NOT
   counted here — they're checked separately by collect-predicates."
  [form]
  (cond
    (predicate-call? form)
    (into #{} (mapcat collect-operators (rest form)))

    (operator-call? form)
    (into #{(first form)}
          (mapcat collect-operators (rest form)))

    (sequential? form)
    (into #{} (mapcat collect-operators form))

    :else #{}))


(defn- schema-predicate-names
  "Extract the set of declared predicate keywords from a schema map.
   The schema's `:predicates` is `{:pred-name {:arg-sorts [...] :return ...}, ...}`."
  [schema]
  (set (keys (get schema :predicates {}))))


(defn- contains-term?
  "Recursively test whether `form` contains `target` as a subterm
   (equal by value). Walks sequential forms and maps."
  [form target]
  (cond
    (= form target) true
    (map? form) (some (fn [[k v]] (or (contains-term? k target)
                                      (contains-term? v target)))
                      form)
    (sequential? form) (some #(contains-term? % target) form)
    :else false))


(defn- on-unsat-defect-id
  "Pull the `:defect` id out of the `:on-unsat` option map, or nil."
  [on-unsat]
  (when (map? on-unsat) (:defect on-unsat)))


;; ----- public surface -------------------------------------------------------


(defn grammar-conforming?
  "Return `{:ok true}` if `edn-form` is a valid BookLogic
   `defconstraint` referencing only schema-declared predicates and
   SUPPORTED-OPERATORS ops, else `{:ok false :tag <kw> :reason <str>}`."
  [edn-form schema]
  (cond
    ;; If the parsed form is not even a sequential — e.g. a bare
    ;; symbol left over from prose like "Sure, here is..." — classify
    ;; it as a non-EDN failure. The LLM did not emit a constraint form
    ;; at all; downstream `:grammar-fail/wrong-head` would be
    ;; misleading.
    (not (sequential? edn-form))
    {:ok false
     :tag :grammar-fail/non-edn
     :reason (str "form is not a sequential constraint expression; "
                  "got " (pr-str edn-form))}

    (not= 'defconstraint (first edn-form))
    {:ok false
     :tag :grammar-fail/wrong-head
     :reason (str "head must be defconstraint, got " (first edn-form))}

    :else
    (let [options (try (apply hash-map (drop 2 edn-form))
                       (catch :default _ nil))
          assert-form (when options (:assert options))
          on-unsat (when options (:on-unsat options))]
      (cond
        (nil? options)
        {:ok false
         :tag :grammar-fail/wrong-head
         :reason "defconstraint keyword-args are malformed (odd count?)"}

        (nil? assert-form)
        {:ok false
         :tag :grammar-fail/wrong-head
         :reason ":assert option is required on a defconstraint"}

        (nil? on-unsat)
        {:ok false
         :tag :grammar-fail/wrong-head
         :reason ":on-unsat option is required on a defconstraint"}

        :else
        (let [used-ops (collect-operators assert-form)
              illegal-ops (cset/difference used-ops SUPPORTED-OPERATORS)]
          (if (seq illegal-ops)
            {:ok false
             :tag :grammar-fail/illegal-op
             :reason (str "illegal operator(s) outside the BookLogic "
                          "supported set: " illegal-ops)}
            (let [used-preds (collect-predicates assert-form)
                  known-preds (schema-predicate-names schema)
                  missing (cset/difference used-preds known-preds)]
              (if (seq missing)
                {:ok false
                 :tag :grammar-fail/unknown-predicate
                 :reason (str "unknown predicate(s) not declared in "
                              "schema: " missing)}
                ;; REQ-TEST-042: a rule whose :assert references its own
                ;; :on-unsat defect id "proves itself" without touching
                ;; the atomspace — reject as a circular definition.
                (let [defect-id (on-unsat-defect-id on-unsat)]
                  (if (and (some? defect-id)
                           (contains-term? assert-form defect-id))
                    {:ok false
                     :tag :grammar-fail/circular-definition
                     :reason (str "assert references its own :on-unsat "
                                  "defect id " defect-id
                                  " (circular self-proof)")}
                    {:ok true}))))))))))


(defn- result->json-string [m]
  "Serialise a result map to a JSON string with stringified tag.
   We do this manually (rather than via `js/JSON.stringify` on a
   clj->js conversion) so the tag's namespace is preserved as
   `grammar-fail/non-edn` rather than `nil`."
  (let [ok (boolean (:ok m))
        tag (:tag m)
        reason (:reason m)
        ;; Keywords like :grammar-fail/non-edn render as a slash-form
        ;; string for the Python side.
        tag-str (when tag
                  (str (when-let [n (namespace tag)] (str n "/"))
                       (name tag)))
        ;; Hand-rolled JSON: only three known fields, all simple.
        esc (fn [s]
              (-> s
                  (str/replace "\\" "\\\\")
                  (str/replace "\"" "\\\"")
                  (str/replace "\n" "\\n")
                  (str/replace "\r" "\\r")
                  (str/replace "\t" "\\t")))
        parts (cond-> [(str "\"ok\": " ok)]
                tag-str (conj (str "\"tag\": \"" (esc tag-str) "\""))
                reason  (conj (str "\"reason\": \"" (esc (str reason)) "\"")))]
    (str "{" (str/join ", " parts) "}")))


(defn grammar-conforming-json
  "JSON-shaped wrapper for Python test consumption.

   Returns a JSON string containing keys `ok` (bool), `tag` (string or
   absent), and `reason` (string or absent). Two early failure modes
   are handled here, before `grammar-conforming?` is called:

     - the form is not parseable EDN → `:grammar-fail/non-edn`
     - the schema is not parseable EDN → a schema-validity error

   Both surface with `ok=false` and a tag the orchestrator can route on."
  [form-str schema-str]
  (let [form-result
        (try {:ok true :value (edn/read-string form-str)}
             (catch :default e
               {:ok false
                :tag :grammar-fail/non-edn
                :reason (str "form is not parseable EDN: "
                             (or (.-message e) e))}))
        schema-result
        (try {:ok true :value (edn/read-string schema-str)}
             (catch :default e
               {:ok false
                :tag :grammar-fail/non-edn
                :reason (str "schema is not parseable EDN: "
                             (or (.-message e) e))}))]
    (cond
      (not (:ok form-result))
      (result->json-string form-result)

      (not (:ok schema-result))
      (result->json-string schema-result)

      :else
      (result->json-string
        (grammar-conforming? (:value form-result) (:value schema-result))))))
