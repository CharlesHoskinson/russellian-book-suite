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
  "Symbol marker for un-translatable / passthrough atoms. Carries no
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

(def QueryResult
  "A cozo query/defect row count, as serialised by ir.rs::emit_verdict."
  [:map
   [:name :string]
   [:rows :int]])

(def CorpusDefect
  "A corpus-scope constraint violation (REQ-CORPUS-053)."
  [:map
   [:constraint-id :string]
   [:subjects      [:vector :string]]
   [:explanation   :string]])

(def GraphSummary
  "kg contradiction summary; emitted only when the kg feature ran."
  [:map
   [:claim-count :int]
   [:contradictions [:vector [:map
                              [:claim-id :string]
                              [:reason   :string]]]]])

(def Verdict
  "Mirror of the keys ir.rs::emit_verdict actually serialises. :status/:core/
   :explanation/:queries/:cozo-defects/:corpus-defects are always emitted (the
   collections may be empty); :graph-summary appears only when the kg pass ran."
  [:map
   [:status        [:enum :sat :unsat :unknown]]
   [:core          {:optional true} [:vector :string]]
   [:explanation   {:optional true} :string]
   [:queries       {:optional true} [:vector QueryResult]]
   [:cozo-defects  {:optional true} [:vector QueryResult]]
   [:corpus-defects {:optional true} [:vector CorpusDefect]]
   [:graph-summary {:optional true} GraphSummary]])

(defn enable-instrumentation! []
  (mi/instrument!
    {:report (fn [type data]
               (throw (ex-info (str "DbC violation: " type) data)))}))
