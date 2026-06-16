(ns osmotic-pressure.ir
  "Atomspace IR — malli schemas for Atom, Formula, Claim, Verdict."
  (:require [malli.core :as m]
            [malli.instrument :as mi]))

(def Sort
  [:or :keyword
   [:map [:kind [:enum :fn]]
         [:args [:vector :keyword]]
         [:ret  :keyword]]
   [:map [:kind [:enum :enum]]
         [:members [:vector :keyword]]]])

(def Atom
  [:map
   [:kind [:enum :symbol :variable :grounded :expression]]
   [:sort Sort]])

(def FlatExpression
  "The flat atom the Rust SMT path (smt.rs::bind_atoms) and the Python
   ingesters consume. bind_atoms reads :kind :predicate :subject :value
   off each atom directly; there is no nested :head/:args tree."
  [:map
   [:kind      [:enum :expression]]
   [:id        :string]
   [:predicate :keyword]
   [:subject   :keyword]
   [:value     [:or :int :double :string :boolean]]])

(def OpaqueMarker
  "Symbol marker for un-translatable atoms. Carries no
   predicate/subject/value, so bind_atoms silently skips it (by design)."
  [:map
   [:kind [:enum :symbol]]
   [:sort {:optional true} Sort]
   [:name {:optional true} :any]])

(def Formula
  [:or FlatExpression OpaqueMarker])

(def Claim
  [:map
   [:id          [:re #"^C\d{3,}$"]]
   [:source      :string]
   [:s           :map]
   [:p           :keyword]
   [:o           :any]
   [:c           [:vector :map]]
   [:modality    [:enum :assertion :hypothesis :definition :counterfactual]]
   [:confidence  [:double {:min 0.0 :max 1.0}]]])

(def Verdict
  [:map
   [:status       [:enum :sat :unsat :unknown]]
   [:verified-claims {:optional true} [:vector Claim]]
   [:core         {:optional true} [:vector :string]]
   [:proofs       {:optional true} [:vector :map]]
   [:graph-summary {:optional true} :map]])

(defn enable-instrumentation! []
  (mi/instrument!
    {:report (fn [type data]
               (throw (ex-info (str "DbC violation: " type) data)))}))
