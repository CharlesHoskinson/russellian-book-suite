(ns epidemiology.nl-to-fol
  "Phase 2: meander rewrite of Claim → Formula."
  (:require [meander.epsilon :as m]))

(defn to-si [v u]
  (case u
    "atm" (* v 101325.0)
    "C"   (+ v 273.15)
    v))

(defn claim->formula [claim]
  (m/rewrite claim
    {:id ?id
     :s  ?subj
     :p  ?pred
     :o  {:kind :quantity :value ?v :unit ?u}
     :c  [!conds ...]}
    {:kind :expression :sort :formula
     :head {:kind :symbol :name :forall :sort :rule}
     :args [{:kind :variable :name "?subj" :sort :entity}
            {:kind :expression :sort :formula
             :head {:kind :symbol :name :implies :sort :rule}
             :args [{:kind :expression :sort :formula
                     :head {:kind :symbol :name :and :sort :rule}
                     :args [!conds ...]}
                    {:kind :expression :sort :formula
                     :head {:kind :symbol :name := :sort :rule}
                     :args [{:kind :expression :sort :real
                             :head {:kind :symbol :name ~?pred :sort :real}
                             :args [{:kind :variable :name "?subj" :sort :entity}]}
                            {:kind :grounded :sort :real
                             :name ~(to-si ?v ?u)
                             :grounded {:lib "literal" :fn "value"}}]}]}]}
    ?other {:kind :symbol :sort :formula :name :OPAQUE}))

(defn translate-corpus [claims]
  (mapv claim->formula claims))
