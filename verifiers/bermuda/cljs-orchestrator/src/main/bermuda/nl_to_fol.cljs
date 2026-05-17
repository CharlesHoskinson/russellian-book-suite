(ns bermuda.nl-to-fol
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

(defn translate-corpus [claims]
  (mapv claim->formula claims))
