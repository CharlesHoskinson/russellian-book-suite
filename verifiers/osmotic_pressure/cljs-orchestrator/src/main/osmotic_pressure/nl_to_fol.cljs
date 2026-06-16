(ns osmotic-pressure.nl-to-fol
  "Phase 2: meander rewrite of Claim → Formula."
  (:require [meander.epsilon :as m]))

(defn to-si [v u]
  (case u
    "atm" (* v 101325.0)
    "C"   (+ v 273.15)
    v))

(defn- ->kw
  "Coerce a subject/predicate token to a keyword. Keywords pass through;
   a subject entity map contributes its :name; strings/symbols are keyword-ified."
  [x]
  (cond
    (keyword? x) x
    (map? x)     (keyword (str (or (:name x) (get x "name") x)))
    :else        (keyword (str x))))

(defn claim->formula [claim]
  ;; Emit the FLAT atom contract the Rust SMT path (smt.rs::bind_atoms) and
  ;; the Python ingesters consume:
  ;;   {:kind :expression :id <id> :predicate <kw> :subject <kw> :value <scalar>}
  ;; to-si unit conversion is preserved on the bound value.
  (m/rewrite claim
    {:id ?id
     :s  ?subj
     :p  ?pred
     :o  {:kind :quantity :value ?v :unit ?u}
     :c  [!conds ...]}
    {:kind      :expression
     :id        ~(str ?id)
     :predicate ~(->kw ?pred)
     :subject   ~(->kw ?subj)
     :value     ~(to-si ?v ?u)}
    ?other {:kind :symbol :sort :formula :name :OPAQUE}))

(defn translate-corpus [claims]
  (mapv claim->formula claims))
