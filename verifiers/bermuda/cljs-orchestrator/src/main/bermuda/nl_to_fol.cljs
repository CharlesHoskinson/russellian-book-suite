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

(defn- ->kw
  "Coerce a subject/predicate token to a keyword. Keywords pass through;
   a subject entity map contributes its :name; strings/symbols are keyword-ified."
  [x]
  (cond
    (keyword? x) x
    (map? x)     (keyword (str (or (:name x) (get x "name") x)))
    :else        (keyword (str x))))

(defn- legacy-claim->formula [claim]
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
    (let [cid (or (:claim/id payload) (get payload "claim/id") "C000")]
      ;; Flat atom: a verified status assertion bound as a boolean predicate.
      {:kind      :expression
       :id        (str cid)
       :predicate :verified
       :subject   (keyword (str cid))
       :value     true})

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
