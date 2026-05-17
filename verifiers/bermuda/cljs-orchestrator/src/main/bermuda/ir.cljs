(ns bermuda.ir
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

(def Formula Atom)

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

(def EventHead
  "Symbolic head produced by the book-knowledge exporter. Stored as a
   symbol in CLJS (cljs.reader reads `claim/verified` as a symbol)."
  [:or :symbol :keyword])

(def Event
  "A trace event read from analysis/ingest-trace.edn. Two-element tuple:
   the first element is the head symbol/keyword (e.g. `claim/verified`),
   the second is a payload map."
  [:tuple EventHead :map])

(def ClaimOrEvent
  "Phase translate input element. Backwards-compatible: either a legacy
   Claim map, or a new Event vector."
  [:or Claim Event])

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
