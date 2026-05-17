(ns bermuda.nl-to-fol
  "Phase 2: meander rewrite of Claim -> Formula.

   Accepts two input shapes per element:
   - Legacy: a Claim map ({:id :s :p :o :c ...}).
   - Trace event: a 2-tuple [head payload] where head is a Symbol or
     Keyword whose namespaced name selects a dispatch branch.

   translate-corpus filters nils, so dispatch branches may return nil
   to drop an element (e.g. source/ingested).

   REQ-CLJS-ORCH-010, REQ-CLJS-ORCH-011: event-stream-aware dispatch."
  (:require [meander.epsilon :as m]))

(defn to-si [v u]
  (case u
    "atm" (* v 101325.0)
    "C"   (+ v 273.15)
    v))

(defn- legacy-claim->formula [claim]
  (m/rewrite claim
    {:id ?id
     :s  ?subj
     :p  ?pred
     :o  {:kind :quantity :value ?v :unit ?u}
     :c  [!conds ...]}
    {:kind :expression :sort :formula
     :head {:kind :symbol :sort :rule}
     :args [{:kind :variable :sort :entity}
            {:kind :expression :sort :formula
             :head {:kind :symbol :sort :rule}
             :args [{:kind :expression :sort :formula
                     :head {:kind :symbol :sort :rule}
                     :args [!conds ...]}
                    {:kind :expression :sort :formula
                     :head {:kind :symbol :sort :rule}
                     :args [{:kind :expression :sort :real
                             :head {:kind :grounded
                                    :sort {:kind :fn :args [:entity] :ret :real}
                                    :name ~?pred
                                    :grounded {:lib "predicate" :fn "lookup"}}
                             :args [{:kind :variable :sort :entity}]}
                            {:kind :grounded :sort :real
                             :name ~(to-si ?v ?u)
                             :grounded {:lib "literal" :fn "value"}}]}]}]}
    ?other {:kind :symbol :sort :formula}))

(defn- head-string [head]
  "Render head Symbol/Keyword/string to its ns/name textual form."
  (cond
    (symbol? head)  (str (namespace head) "/" (name head))
    (keyword? head) (str (namespace head) "/" (name head))
    :else           (str head)))

(defn- event->formula [head payload]
  (case (head-string head)
    "claim/verified"
    {:kind :expression :sort :formula
     :head {:kind :symbol :name :verified :sort :rule}
     :args [{:kind :grounded :sort :string
             :name (or (:claim/id payload) (get payload "claim/id") "C000")
             :grounded {:lib "literal" :fn "claim-id"}}
            {:kind :grounded :sort :string
             :name (or (:text payload) (get payload "text") "")
             :grounded {:lib "literal" :fn "text"}}]}

    "source/ingested"  nil
    "claim/proposed"   nil
    "claim/disputed"   nil
    "claim/superseded" nil
    "claim/refuted"    nil

    "atom/emitted"
    (or (:atom payload) (get payload "atom"))

    ;; Unknown heads — opaque marker
    {:kind :symbol :sort :formula :name :OPAQUE}))

(defn claim->formula [item]
  "Dispatch on input shape: a vector is a trace event; a map is a Claim."
  (cond
    (and (vector? item) (= 2 (count item)))
    (event->formula (first item) (second item))

    (map? item)
    (legacy-claim->formula item)

    :else
    {:kind :symbol :sort :formula :name :OPAQUE}))

(defn translate-corpus [items]
  (into [] (keep claim->formula) items))
