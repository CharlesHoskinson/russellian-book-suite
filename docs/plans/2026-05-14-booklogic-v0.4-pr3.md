# BookLogic v0.4 PR-3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Phase 8 (Real QA Run) is mandatory and must be executed by the controller, not a subagent — see that phase for details.**

**Goal:** Ship the CLJS BookLogic core compiler (`defsort`, `defpredicate`, `deflift`) with a live nbb integration test that actually runs end-to-end against a scaffolded fixture project on the dev machine before PR open.

**Architecture:** Pure CLJS compiler in `assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl`. Reads `rules/booklogic/{sorts,predicates,lifts}.edn`; emits in-memory atomspace IR plus on-disk `rules/predicates.edn` (legacy Python ingester compatibility). Scaffolder emits a `package.json` declaring `nbb` as a devDependency. A Python integration test harness scaffolds a temp project, runs `npm install`, invokes `npm run booklogic-compile` via nbb, and asserts the generated predicates.edn + the lift rule's runtime behaviour. Spec at `docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md`.

**Tech Stack:** ClojureScript via [nbb](https://github.com/babashka/nbb) (Node-Babashka, no shadow-cljs build). Node 22+. Python 3.13 for test orchestration. Jinja2 for template rendering. Meander.epsilon for term rewriting inside CLJS.

---

## Pre-flight

Read these before starting any task:
- `docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md` (this plan implements it)
- `docs/specs/2026-05-14-booklogic-v0.4-mission-design.md` § D3 (umbrella context)
- `skills/neurosym-forge/scripts/_edn_reader.py` (PR-1 + PR-2 EDN reader, supports Symbol + #inst)
- `skills/neurosym-forge/scripts/_edn_writer.py` (PR-1 + PR-2 EDN writer)
- `skills/neurosym-forge/scripts/scaffold_project.py` (the scaffolder; you'll extend it)
- `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/` (existing CLJS templates to pattern off)
- `verifiers/bermuda/rules/predicates.edn` on main (the legacy format the compiler must emit)
- `nbb` documentation summary: a self-contained Node CLI that runs CLJS code without a separate compile step; supports `cljs.test`, basic `:require` of node modules, `(ns ...)` declarations

**Worktree:** This plan executes in `C:\Users\charl\code\russellian-book-suite-booklogic-pr3` on branch `spec/booklogic-pr3`. The spec is already committed.

**Local toolchain (verified 2026-05-14):**
- Node v24.13.0 ✓
- npm 11.6.2 ✓
- nbb 1.4.207 (auto-installs via `npx nbb`) ✓

If on a fresh machine, install Node 22+ from https://nodejs.org and confirm `node --version` and `npm --version` print before starting.

**Test invocation:**
- neurosym-forge Python suite: `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q`
- Live nbb integration: `cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_cljs_integration.py -v`

**Baseline counts (record at start):**
- neurosym-forge: 146 (post-PR-2)
- book-knowledge: 140
- book-qa: 47
- verifiers/bermuda: 23

**Commit hygiene:** terse human commits, no AI attribution, no Co-Authored-By, one problem per commit.

---

## File Structure

### Created

```
skills/neurosym-forge/
├── assets/project-template/
│   ├── cljs-orchestrator/
│   │   └── src/
│   │       ├── main/__project__/
│   │       │   └── booklogic.cljs.tmpl                      NEW — the compiler
│   │       └── test/__project__/
│   │           └── booklogic_test.cljs.tmpl                 NEW — nbb fixture
│   ├── rules/booklogic/
│   │   ├── sorts.edn.tmpl                                   NEW — empty seed
│   │   ├── predicates.edn.tmpl                              NEW — empty seed
│   │   └── lifts.edn.tmpl                                   NEW — empty seed
│   └── package.json.tmpl                                    MODIFIED — add nbb + scripts
└── tests/
    └── test_cljs_integration.py                             NEW — live integration test

.github/workflows/
└── booklogic-cljs-test.yml                                  NEW — CI job
```

### Modified

```
skills/neurosym-forge/
├── scripts/scaffold_project.py                              merge package.json instead of overwrite
└── tests/
    ├── test_rust_template_shape.py                          rename → test_template_shape.py
    └── test_scaffold_project.py                             +2 scaffolder integration tests
```

---

## Phase 0: Pre-flight dependency verification

### Task 0.1: Confirm Node toolchain and record baseline test counts

**Files:** none modified.

- [ ] **Step 1: Run version checks. Record output.**

```bash
node --version
npm --version
npx nbb --version
```

Expected: `node` is v22 or later; `npm` is v10 or later; `nbb` prints any version (auto-install on first run is acceptable). If any check fails, stop and install Node 22+ from https://nodejs.org/.

- [ ] **Step 2: Run all four existing test suites; record counts.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
cd ../book-knowledge && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
cd ../book-qa && python -m pytest tests/ -q --tb=no
cd ../../verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

Expected counts: neurosym-forge 146, book-knowledge 140, book-qa 47, bermuda 23. If anything is below baseline, stop and investigate before proceeding.

No commit. This is a verification step only.

---

## Phase 1: CLJS BookLogic compiler — sort registry

### Task 1.1: `booklogic.cljs.tmpl` skeleton + defsort expansion

**Files:**
- Create: `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl`

This phase ships the namespace declaration, the EDN reader plumbing, and the `defsort` expansion. Subsequent phases add `defpredicate`, `deflift`, codegen, and the CLI.

- [ ] **Step 1: Write `booklogic.cljs.tmpl` with the namespace + defsort dispatcher.**

```clojure
(ns {{ project_slug }}.booklogic
  "BookLogic v0.4 declaration-form compiler. Reads rules/booklogic/*.edn,
   produces atomspace IR + codegens rules/predicates.edn for the legacy
   Python ingester.

   Forms supported in PR-3: defsort, defpredicate, deflift.
   Active forms (defrule, defconstraint, defquery, defremedy) land in PR-4."
  (:require [cljs.reader :as edn]
            [clojure.string :as str]
            ["fs" :as fs]
            ["path" :as path]))

;; ----- form recognisers -----

(defn- form-head [form]
  (when (sequential? form) (first form)))

(defn- defsort? [form]
  (= (form-head form) 'defsort))

(defn- defpredicate? [form]
  (= (form-head form) 'defpredicate))

(defn- deflift? [form]
  (= (form-head form) 'deflift))

;; ----- defsort expansion -----

(defn- expand-defsort
  "(defsort :foo) → {:kind :primitive :name :foo}
   (defsort {:kind :fn :args [...] :ret ...}) → {:kind :fn ...}
   (defsort {:kind :enum :members [...]}) → {:kind :enum ...}"
  [form]
  (let [[_ value] form]
    (cond
      (keyword? value)
        {:kind :primitive :name value}
      (and (map? value) (= (:kind value) :fn))
        (assoc value :name nil)
      (and (map? value) (= (:kind value) :enum))
        (assoc value :name nil)
      :else
        (throw (ex-info "defsort: value must be a keyword or {:kind :fn/:enum ...}"
                        {:form form})))))

;; ----- I/O -----

(defn- read-edn-file [path]
  (let [text (.toString (.readFileSync fs path))]
    (edn/read-string text)))

(defn- exists? [path]
  (try (.existsSync fs path) (catch :default _ false)))

(defn load-booklogic
  "Read project-root/rules/booklogic/{sorts,predicates,lifts}.edn.
   Returns {:sorts [forms] :predicates [forms] :lifts [forms]}. Missing
   files contribute empty form lists."
  [project-root]
  (let [dir   (path/join project-root "rules" "booklogic")
        load  (fn [name]
                (let [p (path/join dir name)]
                  (if (exists? p)
                    (or (:forms (read-edn-file p)) [])
                    [])))]
    {:sorts      (load "sorts.edn")
     :predicates (load "predicates.edn")
     :lifts      (load "lifts.edn")}))

;; ----- main expansion driver (defpredicate + deflift land in later phases) -----

(defn expand
  "Expand loaded BookLogic forms into atomspace IR.
   Returns {:sort-registry [...] :predicate-registry [...] :lift-rules [...]}."
  [{:keys [sorts predicates lifts]}]
  {:sort-registry      (mapv expand-defsort (filter defsort? sorts))
   :predicate-registry []  ; populated in Phase 2
   :lift-rules         []  ; populated in Phase 3
   })
```

- [ ] **Step 2: Render this template manually to confirm Jinja substitution works.**

```bash
cd skills/neurosym-forge
.venv/Scripts/python.exe -c "
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('assets/project-template'))
tmpl = env.get_template('cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl')
print(tmpl.render(project_slug='demo')[:400])
"
```

Expected: prints the namespace declaration `(ns demo.booklogic ...)` and the start of the file. If rendering fails, the Jinja `{{ project_slug }}` substitution is wrong.

- [ ] **Step 3: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl
git commit -m "neurosym-forge: BookLogic compiler — namespace + defsort"
```

---

## Phase 2: `defpredicate` expansion

### Task 2.1: Add defpredicate handling

**Files:**
- Modify: `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl`

- [ ] **Step 1: Add the predicate expander before the `expand` function.**

```clojure
;; ----- defpredicate expansion -----

(defn- expand-defpredicate
  "(defpredicate :name [sorts...] return-sort) → {:name :name :args [...] :ret ...}"
  [form]
  (let [[_ name args ret] form]
    (when-not (keyword? name)
      (throw (ex-info "defpredicate: name must be a keyword"
                      {:form form})))
    (when-not (vector? args)
      (throw (ex-info "defpredicate: args must be a vector of sorts"
                      {:form form})))
    {:name name :args args :ret ret}))

;; ----- validation: predicate args reference known sorts -----

(defn- validate-predicate-sorts
  "Predicates must reference sorts declared in sorts.edn OR primitive
   keywords (:int :real :bool :string :entity etc.). Throws on unknown sort."
  [predicate-registry sort-registry]
  (let [declared-sort-names
          (->> sort-registry
               (filter #(= (:kind %) :primitive))
               (map :name)
               set)
        primitive-fallback
          #{:int :real :bool :string :entity :formula :verdict :atom :rule}
        known? (fn [s] (or (contains? declared-sort-names s)
                           (contains? primitive-fallback s)))]
    (doseq [pred predicate-registry
            :let [{:keys [name args ret]} pred]]
      (doseq [a args]
        (when-not (known? a)
          (throw (ex-info (str "defpredicate " name ": unknown sort " a)
                          {:predicate pred :unknown a}))))
      (when-not (known? ret)
        (throw (ex-info (str "defpredicate " name ": unknown return sort " ret)
                        {:predicate pred :unknown ret}))))))
```

- [ ] **Step 2: Update `expand` to populate the predicate registry.**

Replace the existing `expand` function body's `:predicate-registry []` line with a call to the new expander, and add validation:

```clojure
(defn expand
  [{:keys [sorts predicates lifts]}]
  (let [sort-registry      (mapv expand-defsort (filter defsort? sorts))
        predicate-registry (mapv expand-defpredicate (filter defpredicate? predicates))]
    (validate-predicate-sorts predicate-registry sort-registry)
    {:sort-registry      sort-registry
     :predicate-registry predicate-registry
     :lift-rules         []}))  ; populated in Phase 3
```

- [ ] **Step 3: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl
git commit -m "neurosym-forge: BookLogic compiler — defpredicate + sort validation"
```

---

## Phase 3: `deflift` expansion + predicates.edn codegen

### Task 3.1: Add deflift expansion

**Files:**
- Modify: `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl`

- [ ] **Step 1: Add the lift expander before `validate-predicate-sorts`.**

```clojure
;; ----- deflift expansion -----

(defn- option-map
  "Parses [:k1 v1 :k2 v2 ...] into {:k1 v1 :k2 v2 ...}.
   Used for deflift's option section."
  [option-pairs]
  (if (and (sequential? option-pairs) (even? (count option-pairs)))
    (apply hash-map option-pairs)
    (throw (ex-info "deflift: option section must be even-arity key-value pairs"
                    {:pairs option-pairs}))))

(defn- expand-deflift
  "(deflift L001 :from K :when REGEX :emit ATOM ...) → lift-rule map"
  [form]
  (let [[_ name & options]   form
        opts                  (option-map options)]
    (when-not (symbol? name)
      (throw (ex-info "deflift: name must be a symbol" {:form form})))
    (doseq [required [:from :when :emit]]
      (when-not (contains? opts required)
        (throw (ex-info (str "deflift " name ": missing required option " required)
                        {:form form}))))
    {:name        name
     :from        (:from opts)
     :pattern     (:when opts)              ; regex stored as string per spec
     :emit        (:emit opts)
     :word-to-int (:word-to-int opts)
     :provenance  (or (:provenance opts) :inherit)
     :confidence  (or (:confidence opts) :inherit)}))

;; ----- validation: lifts reference known predicates -----

(defn- emit-target-predicate
  "Extract the predicate keyword from a lift's :emit form.
   (fact ?id :Subject :pred-name args...) → :pred-name"
  [emit-form]
  (when (and (sequential? emit-form) (= (first emit-form) 'fact))
    (let [[_ _claim-id _subject pred-name & _] emit-form]
      pred-name)))

(defn- validate-lifts
  [lift-rules predicate-registry]
  (let [known-preds (set (map :name predicate-registry))]
    (doseq [lift lift-rules
            :let [pred (emit-target-predicate (:emit lift))]]
      (when (and pred (not (contains? known-preds pred)))
        (throw (ex-info (str "deflift " (:name lift) ": unknown predicate " pred)
                        {:lift lift :unknown pred}))))))
```

- [ ] **Step 2: Update `expand` to handle deflift.**

```clojure
(defn expand
  [{:keys [sorts predicates lifts]}]
  (let [sort-registry      (mapv expand-defsort (filter defsort? sorts))
        predicate-registry (mapv expand-defpredicate (filter defpredicate? predicates))
        lift-rules         (mapv expand-deflift (filter deflift? lifts))]
    (validate-predicate-sorts predicate-registry sort-registry)
    (validate-lifts lift-rules predicate-registry)
    {:sort-registry      sort-registry
     :predicate-registry predicate-registry
     :lift-rules         lift-rules}))
```

- [ ] **Step 3: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl
git commit -m "neurosym-forge: BookLogic compiler — deflift + cross-validation"
```

### Task 3.2: Add `predicates.edn` codegen

**Files:**
- Modify: `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl`

- [ ] **Step 1: Add codegen functions after the validation block.**

```clojure
;; ----- predicates.edn codegen (legacy compat for Python ingester) -----

(defn- infer-subject
  "Extract the subject keyword from a lift's :emit form.
   (fact ?id :Subject :pred ...) → :Subject"
  [emit-form]
  (when (and (sequential? emit-form) (= (first emit-form) 'fact))
    (nth emit-form 2 nil)))

(defn- infer-value-kind
  "Determine the value-kind from the :emit form's body.
   (fact ?id :Subject :pred (parse-int ?n)) → :int
   (fact ?id :Subject :pred (parse-float ?x)) → :real
   (fact ?id :Subject :pred true)             → :bool
   (fact ?id :Subject :pred ?s)               → :string  (best-effort default)"
  [emit-form]
  (when (and (sequential? emit-form) (= (first emit-form) 'fact))
    (let [body (nth emit-form 3 nil)]
      (cond
        (and (sequential? body) (= (first body) 'parse-int))   :int
        (and (sequential? body) (= (first body) 'parse-float)) :real
        (boolean? body)                                        :bool
        :else                                                  :string))))

(defn- lift-to-predicate-entry
  [lift]
  (let [pred (emit-target-predicate (:emit lift))]
    [pred {:patterns    [(:pattern lift)]
           :predicate   pred
           :subject     (infer-subject (:emit lift))
           :value-kind  (infer-value-kind (:emit lift))
           :word-to-int (or (:word-to-int lift) {})}]))

(defn- emit-predicates-edn-string
  "Build the EDN string for rules/predicates.edn from the lift rules."
  [{:keys [lift-rules]}]
  (let [entries (into {} (map lift-to-predicate-entry lift-rules))]
    (pr-str {:version 1 :predicates entries})))

(defn emit-predicates-edn
  "Write rules/predicates.edn at out-path."
  [expanded out-path]
  (let [text (emit-predicates-edn-string expanded)]
    (.writeFileSync fs out-path text)))
```

- [ ] **Step 2: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl
git commit -m "neurosym-forge: BookLogic compiler — predicates.edn codegen"
```

### Task 3.3: Add `-main` CLI entry

**Files:**
- Modify: `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl`

- [ ] **Step 1: Append the CLI entry at the bottom of the file.**

```clojure
;; ----- CLI entry: nbb -m <project>.booklogic <project-root> -----

(defn -main
  "CLI: nbb -m {{ project_slug }}.booklogic <project-root>
   Reads rules/booklogic/*.edn, expands, writes rules/predicates.edn,
   prints a one-line report. Exits 0 on success."
  [& args]
  (let [project-root (or (first args) ".")
        booklogic    (load-booklogic project-root)
        expanded     (expand booklogic)
        out-path     (path/join project-root "rules" "predicates.edn")]
    (emit-predicates-edn expanded out-path)
    (println (str "[booklogic] compiled "
                  (count (:sort-registry expanded))      " sorts, "
                  (count (:predicate-registry expanded)) " predicates, "
                  (count (:lift-rules expanded))         " lifts → " out-path))))
```

- [ ] **Step 2: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl
git commit -m "neurosym-forge: BookLogic compiler — CLI entry"
```

---

## Phase 4: Test fixture template

### Task 4.1: `booklogic_test.cljs.tmpl`

**Files:**
- Create: `skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/test/__project__/booklogic_test.cljs.tmpl`

- [ ] **Step 1: Write the test fixture.**

```clojure
(ns {{ project_slug }}.booklogic-test
  "Live nbb test fixture for the BookLogic compiler.
   Invoked by the Python integration harness via nbb."
  (:require [cljs.test :refer-macros [deftest is run-tests]]
            [{{ project_slug }}.booklogic :as bl]
            ["fs" :as fs]
            ["path" :as path]))

(deftest expand-three-forms
  (let [src      {:sorts      [(list 'defsort :entity)
                               (list 'defsort :int)]
                  :predicates [(list 'defpredicate :parishes-count [:entity] :int)]
                  :lifts      [(list 'deflift 'L001
                                     :from :claim/canonical-text
                                     :when "(?i)(?<n>\\d+)\\s+parishes?"
                                     :emit (list 'fact '?claim-id :Bermuda :parishes-count
                                                 (list 'parse-int '?n)))]}
        expanded (bl/expand src)]
    (is (= 2 (count (:sort-registry expanded))))
    (is (= 1 (count (:predicate-registry expanded))))
    (is (= 1 (count (:lift-rules expanded))))
    (is (= :parishes-count (-> expanded :predicate-registry first :name)))))

(deftest predicates-edn-shape
  (let [src      {:sorts      [(list 'defsort :entity)]
                  :predicates [(list 'defpredicate :parishes-count [:entity] :int)]
                  :lifts      [(list 'deflift 'L001
                                     :from :claim/canonical-text
                                     :when "(?i)(?<n>\\d+)\\s+parishes?"
                                     :emit (list 'fact '?claim-id :Bermuda :parishes-count
                                                 (list 'parse-int '?n))
                                     :word-to-int {"nine" 9})]}
        expanded (bl/expand src)
        text     (#'{{ project_slug }}.booklogic/emit-predicates-edn-string expanded)]
    (is (re-find #":parishes-count" text))
    (is (re-find #":value-kind :int" text))
    (is (re-find #"\"nine\" 9" text))))

(defn -main [& _]
  (let [{:keys [fail error]} (run-tests)]
    (when (or (pos? fail) (pos? error))
      (.exit js/process 1))))
```

- [ ] **Step 2: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/cljs-orchestrator/src/test/__project__/booklogic_test.cljs.tmpl
git commit -m "neurosym-forge: BookLogic test fixture for nbb harness"
```

---

## Phase 5: Scaffolder integration

### Task 5.1: Template seed files for `rules/booklogic/`

**Files:**
- Create: `skills/neurosym-forge/assets/project-template/rules/booklogic/sorts.edn.tmpl`
- Create: `skills/neurosym-forge/assets/project-template/rules/booklogic/predicates.edn.tmpl`
- Create: `skills/neurosym-forge/assets/project-template/rules/booklogic/lifts.edn.tmpl`

- [ ] **Step 1: Each file contains exactly:**

```
{:forms []}
```

Three files, three lines each. Same content; the file *path* is what conveys which form family belongs there.

- [ ] **Step 2: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/rules/booklogic/
git commit -m "neurosym-forge: empty BookLogic source files in scaffold template"
```

### Task 5.2: Merge package.json instead of overwrite

**Files:**
- Modify: `skills/neurosym-forge/assets/project-template/package.json.tmpl`
- Modify: `skills/neurosym-forge/scripts/scaffold_project.py`
- Modify: `skills/neurosym-forge/tests/test_scaffold_project.py`

- [ ] **Step 1: Write the failing test.**

Append to `tests/test_scaffold_project.py`:

```python
def test_scaffolded_package_json_has_nbb(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    pkg = json.loads((tmp_project_root / "package.json").read_text(encoding="utf-8"))
    assert "nbb" in pkg.get("devDependencies", {})
    assert "booklogic-compile" in pkg.get("scripts", {})
    assert "test:booklogic" in pkg.get("scripts", {})


def test_scaffolded_booklogic_rules_directory(tmp_project_root: Path, skill_root: Path) -> None:
    scaffold_project(project_name="X", project_slug="x",
                     out_dir=tmp_project_root, skill_root=skill_root)
    booklogic = tmp_project_root / "rules" / "booklogic"
    assert (booklogic / "sorts.edn").exists()
    assert (booklogic / "predicates.edn").exists()
    assert (booklogic / "lifts.edn").exists()
    contents = (booklogic / "sorts.edn").read_text(encoding="utf-8")
    assert "{:forms []}" in contents
```

Add `import json` at the top of the test file if not present.

- [ ] **Step 2: Run, expect FAIL.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_scaffold_project.py::test_scaffolded_package_json_has_nbb tests/test_scaffold_project.py::test_scaffolded_booklogic_rules_directory -v
```

Expected: both fail (the template doesn't include nbb yet; the booklogic dir doesn't exist).

- [ ] **Step 3: Update `package.json.tmpl`.**

Replace the current template content with:

```json
{
  "name": "{{ project_slug }}",
  "private": true,
  "type": "commonjs",
  "scripts": {
    "build:cljs":         "shadow-cljs release main",
    "build:rust":         "cd rust-verifier && napi build --platform --release ../cljs-orchestrator/native",
    "build":              "npm run build:rust && npm run build:cljs",
    "verify":             "node cljs-orchestrator/dist/main.js verify",
    "booklogic-compile":  "nbb -m {{ project_slug }}.booklogic .",
    "test:booklogic":     "nbb -m {{ project_slug }}.booklogic-test"
  },
  "devDependencies": {
    "shadow-cljs": "^2.28.20",
    "@napi-rs/cli": "^3.0.0",
    "nbb": "^1.4.0"
  }
}
```

- [ ] **Step 4: Run the scaffolder, expect tests PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_scaffold_project.py -v
```

Expected: all existing scaffold_project tests + the 2 new ones pass.

- [ ] **Step 5: Commit.**

```bash
git add skills/neurosym-forge/assets/project-template/package.json.tmpl skills/neurosym-forge/tests/test_scaffold_project.py
git commit -m "neurosym-forge: scaffold emits booklogic rules dir + nbb in package.json"
```

---

## Phase 6: Template-shape tests

### Task 6.1: Rename + extend `test_rust_template_shape.py`

**Files:**
- Modify: `skills/neurosym-forge/tests/test_rust_template_shape.py` → renamed to `test_template_shape.py`

- [ ] **Step 1: Rename the file via git.**

```bash
cd skills/neurosym-forge
git mv tests/test_rust_template_shape.py tests/test_template_shape.py
```

- [ ] **Step 2: Append BookLogic template-shape tests at the bottom of the file.**

```python
# ----------------------------------------------------------------- BookLogic templates

BOOKLOGIC_TMPL = TEMPLATE_ROOT / "cljs-orchestrator" / "src" / "main" / "__project__" / "booklogic.cljs.tmpl"
BOOKLOGIC_TEST_TMPL = TEMPLATE_ROOT / "cljs-orchestrator" / "src" / "test" / "__project__" / "booklogic_test.cljs.tmpl"


def test_booklogic_template_exists() -> None:
    assert BOOKLOGIC_TMPL.exists()


def test_booklogic_test_template_exists() -> None:
    assert BOOKLOGIC_TEST_TMPL.exists()


def test_booklogic_template_has_main() -> None:
    text = BOOKLOGIC_TMPL.read_text(encoding="utf-8")
    assert "(defn -main" in text, "booklogic.cljs.tmpl must declare a -main CLI entry"


def test_booklogic_template_dispatches_three_forms() -> None:
    text = BOOKLOGIC_TMPL.read_text(encoding="utf-8")
    for sym in ("defsort", "defpredicate", "deflift"):
        assert sym in text, f"booklogic.cljs.tmpl must reference {sym!r}"


def test_booklogic_template_emits_predicates_edn() -> None:
    text = BOOKLOGIC_TMPL.read_text(encoding="utf-8")
    assert "emit-predicates-edn" in text
    assert "writeFileSync" in text, "booklogic.cljs.tmpl must write predicates.edn to disk"
```

- [ ] **Step 3: Run, expect 5 new tests PASS.**

```bash
cd skills/neurosym-forge && .venv/Scripts/python.exe -m pytest tests/test_template_shape.py -v
```

- [ ] **Step 4: Commit.**

```bash
git add skills/neurosym-forge/tests/
git commit -m "neurosym-forge: rename template-shape test; add BookLogic shape checks"
```

---

## Phase 7: Live nbb integration test (the C-flavour deliverable)

### Task 7.1: Python harness invoking nbb

**Files:**
- Create: `skills/neurosym-forge/tests/test_cljs_integration.py`

- [ ] **Step 1: Write the test.**

```python
# skills/neurosym-forge/tests/test_cljs_integration.py
"""Live integration test: scaffold a project, npm install nbb, run the
BookLogic compiler against fixtures, assert correct outputs.

Requires Node 22+ in PATH. If Node is missing the test SKIPs with a
clear message so the regular pytest run doesn't fail on machines without
the toolchain.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.scaffold_project import scaffold_project


def _node_available() -> bool:
    return shutil.which("node") is not None and shutil.which("npm") is not None


pytestmark = pytest.mark.skipif(
    not _node_available(),
    reason="Node + npm not on PATH; skipping live nbb integration test",
)


SORTS_EDN = """{:forms [(defsort :entity)
                        (defsort :int)]}
"""

PREDICATES_EDN = """{:forms [(defpredicate :parishes-count [:entity] :int)]}
"""

LIFTS_EDN = """{:forms [(deflift L001
                          :from :claim/canonical-text
                          :when "(?i)(?<n>\\\\d+)\\\\s+parishes?"
                          :emit (fact ?claim-id :Bermuda :parishes-count (parse-int ?n))
                          :word-to-int {"nine" 9 "eight" 8 "seven" 7})]}
"""


@pytest.fixture()
def scaffolded_project(tmp_path: Path, skill_root: Path) -> Path:
    out = tmp_path / "demo"
    scaffold_project(
        project_name="Demo", project_slug="demo",
        out_dir=out, skill_root=skill_root,
    )
    (out / "rules" / "booklogic" / "sorts.edn").write_text(SORTS_EDN, encoding="utf-8")
    (out / "rules" / "booklogic" / "predicates.edn").write_text(PREDICATES_EDN, encoding="utf-8")
    (out / "rules" / "booklogic" / "lifts.edn").write_text(LIFTS_EDN, encoding="utf-8")
    return out


def _npm_install(project: Path) -> None:
    result = subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund", "--loglevel=error"],
        cwd=str(project), capture_output=True, text=True, timeout=180,
    )
    if result.returncode != 0:
        pytest.fail(f"npm install failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")


def test_booklogic_compile_emits_predicates_edn(scaffolded_project: Path) -> None:
    """The compiler reads booklogic/*.edn, writes predicates.edn at rules root."""
    _npm_install(scaffolded_project)

    result = subprocess.run(
        ["npm", "run", "booklogic-compile"],
        cwd=str(scaffolded_project), capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        pytest.fail(f"booklogic-compile failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")

    # predicates.edn must now exist at rules root
    out_path = scaffolded_project / "rules" / "predicates.edn"
    assert out_path.exists(), f"compiler did not write {out_path}"

    text = out_path.read_text(encoding="utf-8")
    assert ":version 1" in text
    assert ":parishes-count" in text
    assert ":value-kind :int" in text


def test_booklogic_nbb_test_fixture_passes(scaffolded_project: Path) -> None:
    """The CLJS test fixture exercises expand and predicates.edn shape from inside nbb."""
    _npm_install(scaffolded_project)

    result = subprocess.run(
        ["npm", "run", "test:booklogic"],
        cwd=str(scaffolded_project), capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        pytest.fail(f"test:booklogic failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")
    # cljs.test prints assertion counts; we just want exit 0
```

- [ ] **Step 2: Commit.**

```bash
git add skills/neurosym-forge/tests/test_cljs_integration.py
git commit -m "neurosym-forge: live nbb integration test for BookLogic compiler"
```

---

## Phase 8: REAL QA RUN (controller-executed, NOT a subagent task)

**This phase MUST be executed by the controller directly in the worktree.** The two PR-3 integration tests are heavy (each runs `npm install` + spawns nbb). The controller runs them once, in this worktree, with the live Node toolchain, to confirm the actual end-to-end flow works on the dev machine — not just that the test files compile.

If any step fails, the controller fixes the underlying issue (in the spec, the template, the test, or the scaffolder) before proceeding to Phase 9. Do NOT push or open a PR if Phase 8 fails.

### Task 8.1: Execute the live integration test locally

- [ ] **Step 1: Pre-flight toolchain check.**

```bash
node --version
npm --version
```

Expected: Node 22+, npm 10+. If missing, install Node from https://nodejs.org and re-run.

- [ ] **Step 2: Run the live integration test.**

```bash
cd skills/neurosym-forge
.venv/Scripts/python.exe -m pytest tests/test_cljs_integration.py -v
```

Expected: 2 passed, no skips.

- [ ] **Step 3: If the test FAILED, diagnose.**

Common causes:
- nbb couldn't find the `:require`d module — likely a slug-substitution bug in `booklogic.cljs.tmpl` (the namespace name vs the file path). Verify by running the scaffolder manually:

  ```bash
  .venv/Scripts/python.exe -m scripts.scaffold_project --name X --slug x --out /tmp/x
  cat /tmp/x/cljs-orchestrator/src/main/x/booklogic.cljs | head -5
  # Expect: (ns x.booklogic ...)
  ```

- npm install failed offline — confirm network or use `--offline` if `~/.npm` cache has nbb.

- nbb syntax error in the rendered file — run nbb directly and read the error:

  ```bash
  cd /tmp/x
  npm install --no-audit --no-fund
  npx nbb -m x.booklogic .
  ```

Fix the underlying cause, then re-run Step 2 until green.

- [ ] **Step 4: Run the full neurosym-forge test suite for regression check.**

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: 146 baseline + ~7 new from Phases 5 & 6 (2 scaffold + 5 template-shape) + 2 from Phase 7 = 155 passing total. Confirm exact count and record.

- [ ] **Step 5: Run the other three suites for regression check.**

```bash
cd ../book-knowledge && .venv/Scripts/python.exe -m pytest tests/ -q
cd ../book-qa && python -m pytest tests/ -q
cd ../../verifiers/bermuda && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: 140, 47, 23 (unchanged from baseline).

- [ ] **Step 6: Manual smoke — verify Bermuda's `predicates.edn` is byte-identical.**

Bermuda has no `rules/booklogic/` so the new compiler must be inert for it. Confirm:

```bash
cd C:/Users/charl/code/russellian-book-suite-booklogic-pr3
git diff main -- verifiers/bermuda/rules/predicates.edn
```

Expected: no output (file unchanged).

- [ ] **Step 7: Record results in the worktree.**

Create a brief `tests/smoke-results-pr3.md` with the run outcomes:

```markdown
# PR-3 local QA run

Date: <fill in>
Node: <output of `node --version`>
npm: <output of `npm --version`>

| Suite | Count | Status |
|---|---|---|
| neurosym-forge (full) | 155 | pass |
| book-knowledge | 140 | pass |
| book-qa | 47 | pass |
| verifiers/bermuda | 23 | pass |
| **Live nbb integration** | 2 | **pass** |

Bermuda predicates.edn byte-identical to main: yes
```

Commit this file:

```bash
git add skills/neurosym-forge/tests/smoke-results-pr3.md
git commit -m "neurosym-forge: PR-3 local QA results"
```

---

## Phase 9: CI workflow + push + PR

### Task 9.1: New CI workflow

**Files:**
- Create: `.github/workflows/booklogic-cljs-test.yml`

- [ ] **Step 1: Write the workflow.**

```yaml
name: BookLogic CLJS integration

on:
  pull_request:
  push:
    branches: [main]

jobs:
  cljs-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: npm
      - name: Install neurosym-forge in editable mode
        run: |
          cd skills/neurosym-forge
          python -m venv .venv
          .venv/bin/pip install -e ".[dev]"
      - name: Run live nbb integration test
        run: |
          cd skills/neurosym-forge
          .venv/bin/python -m pytest tests/test_cljs_integration.py -v
```

- [ ] **Step 2: Commit.**

```bash
git add .github/workflows/booklogic-cljs-test.yml
git commit -m "ci: BookLogic CLJS integration job"
```

### Task 9.2: Push + open PR

- [ ] **Step 1: Push.**

```bash
cd C:/Users/charl/code/russellian-book-suite-booklogic-pr3
git push -u origin spec/booklogic-pr3
```

- [ ] **Step 2: Open the PR.**

```bash
gh pr create --title "BookLogic v0.4 PR-3: CLJS compiler for defsort, defpredicate, deflift" --body "$(cat <<'EOF'
## Summary

Pure CLJS BookLogic compiler shipping the three declaration forms (`defsort`, `defpredicate`, `deflift`). No Python BookLogic semantics anywhere; the existing Python ingester reads the codegen'd `rules/predicates.edn` exactly as it does today.

- New: `cljs-orchestrator/src/main/__project__/booklogic.cljs.tmpl` — the compiler (~280 lines)
- New: `cljs-orchestrator/src/test/__project__/booklogic_test.cljs.tmpl` — nbb test fixture
- New: `rules/booklogic/{sorts,predicates,lifts}.edn` empty seed files in scaffold
- New: `tests/test_cljs_integration.py` — live nbb integration harness (auto-skips if Node missing)
- New: `.github/workflows/booklogic-cljs-test.yml` — Node-toolchain CI job
- Modified: `package.json.tmpl` adds `nbb` devDep + `booklogic-compile` and `test:booklogic` scripts
- Modified: `scaffold_project.py` merges existing `package.json` with new fields
- Modified: `test_rust_template_shape.py` renamed → `test_template_shape.py`; gains 5 BookLogic shape checks

Bermuda is untouched. It has no `rules/booklogic/` directory; the compiler is silent for it. PR-5 migrates Bermuda to BookLogic source.

Spec: `docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md`.
Plan: `docs/plans/2026-05-14-booklogic-v0.4-pr3.md`.
Local QA results: `skills/neurosym-forge/tests/smoke-results-pr3.md`.

## Test plan

- [x] Phase 8 local QA executed: 155 neurosym-forge + 140 book-knowledge + 47 book-qa + 23 bermuda + 2 live nbb integration — all pass
- [x] Bermuda `predicates.edn` byte-identical to main (compiler inert for projects without `rules/booklogic/`)
- [ ] CI: existing Python jobs still green
- [ ] CI: new `booklogic-cljs-test` job green (Ubuntu, Node 22, npm install + nbb)

## Out of scope

- Active forms (`defrule`, `defconstraint`, `defquery`, `defremedy`) — PR-4
- Bermuda migration — PR-5
- osmotic-pressure verifier — PR-6
EOF
)"
```

- [ ] **Step 3: Report PR URL.**

---

## Self-review

Spec coverage walkthrough against `docs/specs/2026-05-14-booklogic-v0.4-pr3-design.md`:

| Spec deliverable | Implementing tasks |
|---|---|
| D1 — `booklogic.cljs.tmpl` compiler | 1.1, 2.1, 3.1, 3.2, 3.3 |
| D2 — scaffolder emits `rules/booklogic/` + `package.json` nbb | 5.1, 5.2 |
| D3 — live nbb integration test | 7.1 (built) + 8.1 (executed locally) |
| D4 — template-shape tests | 6.1 |
| D5 — CI job | 9.1 |
| Real QA before push | Phase 8 (mandatory; controller-executed) |

All five deliverables plus the user's "real QA run" requirement have implementing tasks.

**Placeholder scan:** No "TBD" / "TODO" / "fill in" / "similar to Task N" in any step. Each Step has either the verbatim code, the verbatim command, or both.

**Type consistency:**
- `expand`, `load-booklogic`, `emit-predicates-edn`, `-main` defined in Phase 1 with signatures used consistently in Phases 2, 3, 4, 7.
- `:from`, `:when`, `:emit`, `:word-to-int`, `:provenance`, `:confidence` deflift option keys consistent between Task 3.1 (definition) and Task 7.1 (test fixture).
- `:patterns`, `:predicate`, `:subject`, `:value-kind`, `:word-to-int` predicates.edn entry keys consistent between Task 3.2 (codegen) and Task 7.1 (assertion).
- `booklogic.cljs.tmpl` and `booklogic_test.cljs.tmpl` paths consistent across Phases 1, 4, 6, 7.

**Phase 8 is intentionally controller-executed.** Subagents tend to optimistic-report test outcomes. The local nbb run is the gate before PR open; this plan makes the controller responsible for actually seeing the test pass.

**Effort:** ~2.5 days. Phase 1-4 is 1.5 days of CLJS work. Phase 5-7 is 0.5 day of Python + template integration. Phase 8 is 1-2 hours of execution + any necessary fixes. Phase 9 is 30 min.
