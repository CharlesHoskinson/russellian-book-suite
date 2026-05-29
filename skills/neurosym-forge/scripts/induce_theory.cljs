(ns induce-theory
  "Tier 6 Phase W — candidate-generation orchestrator (REQ-INDUCE-050..057).

   The framework's first nbb-driven Python-equivalent. Mirrors the Python
   orchestrator in `_induction_orchestrator.py` and the source helpers in
   `_induction_sources.py`; the two implementations must stay in step.

   Pipeline:
     1. Load schema (rules/booklogic-schema.edn) and atomspace
        (rules/atomspace.edn).
     2. Horn-body mining over the atomspace.
     3. Popper-style typed search over the schema.
     4. LLM proposer (Phase V helper when available, else local Stub).
     5. Dedup by canonical S-expr form (alpha-rename).
     6. Persist queue to work/induction/candidates.edn (REQ-INDUCE-055).

   Phase V's `_induction_grammar.cljs` is loaded conditionally — when
   absent the orchestrator tags candidates `:grammar-unvalidated` for the
   downstream solver to handle, matching Phase U's conditional-import
   pattern. The ranking step (REQ-INDUCE-053) and the budget tracker
   (REQ-INDUCE-056) are wired in follow-on commits."
  (:require [cljs.reader :as edn]
            [clojure.string :as str]
            ["fs" :as fs]
            ["path" :as path]))

;; ----- env helpers -----

(defn- env [name default]
  (let [v (try (aget (.-env js/process) name) (catch :default _ nil))]
    (if (and v (not= v "")) v default)))

(defn- per-source-cap []
  (let [raw (env "NEUROSYM_INDUCTION_CANDIDATES_PER_SOURCE" "20")]
    (or (try (js/parseInt raw 10) (catch :default _ 20)) 20)))

(defn- budget-limit []
  (let [raw (env "NEUROSYM_INDUCTION_BUDGET_USD" nil)]
    (when raw (try (js/parseFloat raw) (catch :default _ nil)))))

(defn- stub-cost []
  (let [raw (env "NEUROSYM_INDUCTION_STUB_COST_USD" "0.001")]
    (or (try (js/parseFloat raw) (catch :default _ 0.001)) 0.001)))

;; ----- I/O -----

(defn- exists? [p]
  (try (.existsSync fs p) (catch :default _ false)))

(defn- read-edn-file [p]
  (let [text (.toString (.readFileSync fs p))]
    (edn/read-string text)))

(defn- write-edn-file [p value]
  (let [dir (path/dirname p)]
    (when-not (exists? dir) (.mkdirSync fs dir #js {:recursive true}))
    (.writeFileSync fs p (pr-str value))))

(defn- write-json-file [p value]
  (let [dir (path/dirname p)]
    (when-not (exists? dir) (.mkdirSync fs dir #js {:recursive true}))
    (.writeFileSync fs p (.stringify js/JSON (clj->js value) nil 2))))

;; ----- canonical S-expr form (REQ-INDUCE-052) -----

(defn canonical-constraint-form
  "Alpha-rename logic variables to ?v0, ?v1, ... and collapse whitespace.
   First-occurrence order of distinct ?ids is the canonical sequence."
  [edn-str]
  (let [pattern #"\?[A-Za-z_][A-Za-z0-9_-]*"
        seen (atom {})
        counter (atom 0)
        renamed (str/replace edn-str pattern
                  (fn [match]
                    (or (get @seen match)
                        (let [next-name (str "?v" @counter)]
                          (swap! counter inc)
                          (swap! seen assoc match next-name)
                          next-name))))]
    (str/replace (str/trim renamed) #"\s+" " ")))

;; ----- schema + atomspace loaders -----

(defn load-schema [project-root]
  (let [p (path/join project-root "rules" "booklogic-schema.edn")]
    (if (exists? p) (read-edn-file p) {:version 1 :predicates {} :sorts []})))

(defn load-atoms [project-root]
  (let [p (path/join project-root "rules" "atomspace.edn")]
    (if (exists? p)
      (let [data (read-edn-file p)]
        (mapv (fn [a]
                {:claim-id (:claim-id a)
                 :document (:document a)
                 :predicate (let [p (:predicate a)]
                              (if (keyword? p) (name p) (str p)))
                 :subject (let [s (:subject a)]
                            (if (keyword? s) (name s) (str s)))
                 :value (:value a)})
              (or (:atoms data) [])))
      [])))

;; ----- Source 1: Horn-body mining (REQ-INDUCE-051(a), 054) -----

(defn horn-mine
  "Enumerate frequent predicate-pair co-occurrence over the atomspace.
   Groups atoms by (document, subject) so subject identity is respected.
   <10 atoms → skip with structured warning (REQ-INDUCE-054)."
  [atoms _schema]
  (if (< (count atoms) 10)
    []
    (let [by-key (reduce (fn [acc a]
                           (update acc [(:document a) (:subject a)]
                                   (fnil conj #{}) (:predicate a)))
                         {} atoms)
          pair-count (atom {})
          pair-atoms (atom {})]
      (doseq [[[doc subj] preds] by-key]
        (let [sorted-preds (sort preds)
              pairs (for [i (range (count sorted-preds))
                          j (range (inc i) (count sorted-preds))]
                      [(nth sorted-preds i) (nth sorted-preds j)])]
          (doseq [pair pairs]
            (swap! pair-count update pair (fnil inc 0))
            (doseq [a atoms
                    :when (and (= (:document a) doc)
                               (= (:subject a) subj)
                               (some #(= (:predicate a) %) pair))]
              (swap! pair-atoms update pair (fnil conj #{}) (:claim-id a))))))
      (let [cap (per-source-cap)
            sorted-pairs (->> @pair-count
                              (sort-by (comp - val))
                              (take cap))]
        (mapv (fn [[[p1 p2] support]]
                (let [edn-str (str "(defconstraint :induced/" p1 "-" p2 "\n"
                                   "  :backend :z3\n"
                                   "  :assert (=> (:" p1 " ?d) (:" p2 " ?d))\n"
                                   "  :on-unsat {:defect :D-induced-h :severity :advisory\n"
                                   "             :message \"Horn-body co-occurrence: " p1 " → " p2 "\"})")]
                  {:id (str "horn-" p1 "-" p2)
                   :canonical-form (canonical-constraint-form edn-str)
                   :edn edn-str
                   :cited-atoms (vec (sort (get @pair-atoms [p1 p2] [])))
                   :origin [:horn-body]
                   :support support
                   :coherence nil
                   :literal-count 2
                   :status :pending
                   :rejection-reason nil}))
              sorted-pairs)))))

;; ----- Source 2: Popper-style typed search (REQ-INDUCE-051(b)) -----

(defn popper-search
  "Typed top-down enumeration up to 4 literals per rule.
   For each pair of :real-returning predicates over the same binding sort,
   emit (approx= (:P ?d) (:Q ?d) :tolerance ε); Phase X fills ε."
  [schema]
  (let [preds (:predicates schema)
        real-preds (filter (fn [[_ sig]] (= (:return sig) :real)) preds)
        by-sort (reduce (fn [acc [pname sig]]
                          (update acc (vec (or (:arg-sorts sig) []))
                                  (fnil conj []) (name pname)))
                        {}
                        (mapv (fn [[k v]] [k v]) real-preds))
        cap (per-source-cap)]
    (loop [groups (vals by-sort)
           out []]
      (cond
        (empty? groups) (vec out)
        (>= (count out) cap) (vec out)
        :else
        (let [names (sort (first groups))
              pairs (for [i (range (count names))
                          j (range (inc i) (count names))]
                      [(nth names i) (nth names j)])
              new-cands (for [[p1 p2] pairs
                              :let [edn-str (str "(defconstraint :induced/" p1 "~" p2 "\n"
                                                 "  :backend :z3\n"
                                                 "  :assert (approx= (:" p1 " ?d) (:" p2 " ?d) :tolerance 0.05)\n"
                                                 "  :on-unsat {:defect :D-induced-p :severity :advisory\n"
                                                 "             :message \"Popper-typed approx eq: " p1 " ≈ " p2 "\"})")]]
                          {:id (str "popper-" p1 "-" p2)
                           :canonical-form (canonical-constraint-form edn-str)
                           :edn edn-str
                           :cited-atoms []
                           :origin [:popper]
                           :support nil
                           :coherence nil
                           :literal-count 4
                           :status :pending
                           :rejection-reason nil})
              combined (vec (concat out new-cands))]
          (recur (rest groups) (vec (take cap combined))))))))

;; ----- Source 3: LLM proposer (Phase V or local Stub) (REQ-INDUCE-051(c)) -----

(defn- stub-propose
  "Deterministic LLM-shape stub. Returns a single candidate per cluster
   keyed on the cluster's first predicate.

   Phase V's _induction_grammar.cljs is the real grammar enforcer; when
   absent we tag the candidate :grammar-unvalidated for downstream
   handling (matches Phase U's conditional-import pattern)."
  [cluster _schema phase-v-available?]
  (when (seq cluster)
    (let [pred (:predicate (first cluster))
          cited (vec (sort (distinct (map :claim-id cluster))))
          edn-str (str "(defconstraint :induced/llm-" pred "\n"
                       "  :backend :z3\n"
                       "  :assert (> (:" pred " ?d) 0)\n"
                       "  :on-unsat {:defect :D-induced-l :severity :advisory\n"
                       "             :message \"LLM-proposed: " pred " > 0\"})")]
      {:id (str "llm-" pred)
       :canonical-form (canonical-constraint-form edn-str)
       :edn edn-str
       :cited-atoms cited
       :origin (if phase-v-available? [:llm] [:llm :grammar-unvalidated])
       :support nil
       :coherence nil
       :literal-count 2
       :status :pending
       :rejection-reason nil})))

(defn- phase-v-grammar-available? []
  ;; The grammar enforcer file is added by the parallel Phase V branch.
  ;; We probe both the current cwd and the script's neighbour directory.
  (let [cwd (try (.cwd js/process) (catch :default _ "."))
        candidates [(path/join cwd "scripts" "_induction_grammar.cljs")
                    (path/join cwd "_induction_grammar.cljs")]]
    (boolean (some exists? candidates))))

(defn llm-propose-clusters
  "REQ-INDUCE-056: per-cluster LLM propose with budget tracking. Returns
   {:candidates [...] :spent-usd N :halted? bool}. When budget is
   exhausted, halts and returns the partial collection so Horn-body and
   Popper sources remain unaffected."
  [clusters schema budget-state]
  (let [phase-v? (phase-v-grammar-available?)
        cost (stub-cost)
        limit (:limit-usd budget-state)]
    (loop [todo clusters
           out []
           spent (:spent-usd budget-state)
           halted? (:halted? budget-state)]
      (if (or (empty? todo) halted?)
        {:candidates out :spent-usd spent :halted? halted?}
        (let [can-spend? (or (nil? limit) (<= (+ spent cost) (+ limit 1e-9)))]
          (if-not can-spend?
            {:candidates out :spent-usd spent :halted? true}
            (let [cand (stub-propose (first todo) schema phase-v?)
                  spent' (+ spent cost)
                  halted'? (and (some? limit) (>= spent' limit))]
              (recur (rest todo)
                     (if cand (conj out cand) out)
                     spent'
                     halted'?))))))))

;; ----- Clusters -----

(defn atom-clusters
  "Group atoms by predicate name. Tier 7 will replace this with
   Phase Q embedding clusters; the predicate-grouped form is the
   deterministic Tier 6 minimum."
  [atoms]
  (let [grouped (group-by :predicate atoms)]
    (mapv #(get grouped %) (sort (keys grouped)))))

;; ----- Dedup (REQ-INDUCE-052) -----

(defn- merge-uniq [a b]
  (let [seen (atom (set a))]
    (vec (concat a
                 (filter (fn [x]
                           (when-not (contains? @seen x)
                             (swap! seen conj x)
                             true))
                         b)))))

(defn dedup
  "Collapse alpha-equivalent candidates and union the origin tags +
   cited atoms. Canonicalisation runs here so callers may pass raw EDN
   forms with arbitrary logic-variable names."
  [candidates]
  (loop [todo candidates
         by-key {}
         order []]
    (if (empty? todo)
      (mapv by-key order)
      (let [c (first todo)
            key (canonical-constraint-form (:canonical-form c))
            existing (get by-key key)]
        (if existing
          (recur (rest todo)
                 (assoc by-key key
                        (-> existing
                            (assoc :origin (merge-uniq (:origin existing) (:origin c)))
                            (assoc :cited-atoms
                                   (merge-uniq (:cited-atoms existing) (:cited-atoms c)))
                            (assoc :support
                                   (if (and (some? (:support existing))
                                            (some? (:support c)))
                                     (+ (:support existing) (:support c))
                                     (or (:support c) (:support existing))))))
                 order)
          (recur (rest todo)
                 (assoc by-key key (assoc c :canonical-form key))
                 (conj order key)))))))

(defn dedup-with-rejection-log [candidates]
  (let [merged (dedup candidates)
        seen (atom #{})
        rejected (atom [])]
    (doseq [c candidates]
      (let [k (canonical-constraint-form (:canonical-form c))]
        (if (contains? @seen k)
          (swap! rejected conj (-> c
                                   (assoc :status :rejected)
                                   (assoc :rejection-reason :duplicate)))
          (swap! seen conj k))))
    {:survivors merged :rejected @rejected}))

;; ----- Persistence -----

(defn- format-id [i]
  (let [s (str i)]
    (apply str (concat (repeat (max 0 (- 3 (count s))) "0") s))))

(defn- candidate->edn [c cid]
  {:id cid
   :canonical-form (:canonical-form c)
   :origin (vec (:origin c))
   :cited-atoms (vec (:cited-atoms c))
   :coherence (:coherence c)
   :support (:support c)
   :literal-count (or (:literal-count c) 0)
   :status (or (:status c) :pending)
   :rejection-reason (:rejection-reason c)})

(defn persist-budget
  "REQ-INDUCE-056: log spend + halt status to work/induction/budget.json."
  [project-root budget]
  (write-json-file (path/join project-root "work" "induction" "budget.json")
                   {:limit_usd (:limit-usd budget)
                    :spent_usd (:spent-usd budget)
                    :llm_halted (boolean (:halted? budget))}))

(defn persist-queue [project-root survivors rejected corpus-size]
  (let [out-dir (path/join project-root "work" "induction")
        out (path/join out-dir "candidates.edn")
        queue (vec (concat
                    (map-indexed (fn [i c] (candidate->edn c (str "c-" (format-id i))))
                                 survivors)
                    (map-indexed (fn [i c] (candidate->edn c (str "r-" (format-id i))))
                                 rejected)))]
    (write-edn-file out
                    {:version 1
                     :generated-at (.toISOString (js/Date.))
                     :corpus-size corpus-size
                     :candidates queue})))

;; ----- main -----

(defn -main
  "CLI: nbb -m induce-theory <project-root>
   or:  nbb induce_theory.cljs <project-root>"
  [& args]
  (let [project-root (or (first args) ".")
        schema (load-schema project-root)
        atoms (load-atoms project-root)
        horn-cands (horn-mine atoms schema)
        popper-cands (popper-search schema)
        budget0 {:limit-usd (budget-limit) :spent-usd 0.0 :halted? false}
        llm-result (llm-propose-clusters (atom-clusters atoms) schema budget0)
        llm-cands (:candidates llm-result)
        budget {:limit-usd (:limit-usd budget0)
                :spent-usd (:spent-usd llm-result)
                :halted? (:halted? llm-result)}
        all (vec (concat horn-cands popper-cands llm-cands))
        {:keys [survivors rejected]} (dedup-with-rejection-log all)]
    (persist-queue project-root survivors rejected (count atoms))
    (persist-budget project-root budget)
    (println (str "[induce-theory] " (count survivors) " candidates, "
                  (count rejected) " rejected, "
                  "spent $" (:spent-usd budget) " of "
                  (if-let [l (:limit-usd budget)] (str "$" l) "unbounded")))))

;; When invoked as `nbb <file> <args>`, nbb runs the file top-to-bottom and
;; does NOT auto-call -main. Inspect argv: if argv[2] is a file path matching
;; this script, drop the leading runtime args and invoke -main with the rest.
;; When invoked as `nbb -m induce-theory <args>`, nbb's main resolver calls
;; -main directly, so this branch SHOULD NOT also fire — argv[2] is "-m" or
;; the namespace name, not a file path.
(let [argv (vec (.-argv js/process))
      script-arg (get argv 2)
      is-file-mode? (and script-arg
                         (or (.endsWith script-arg "induce_theory.cljs")
                             (.endsWith script-arg "induce_theory.cljc")))]
  (when is-file-mode?
    (apply -main (drop 3 argv))))
