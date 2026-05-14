# Russell Corpus Map

This corpus gives `russellian-style` a larger calibration base without loading long source passages into `SKILL.md`.

The corpus contains 50 paragraph pointers from six public-domain Project Gutenberg texts. Each row identifies the source paragraph by URL and line hint, then records the paragraph's rhetorical function. The machine-readable index lives at `assets/russell-corpus/index.json`.

Do not paste the full paragraphs into prompts by default. Retrieve only the paragraph needed for the current comparison, and cite the source URL in any report.

## Source Mix

| Source ID | Title | Paragraphs | Mode |
| --- | --- | ---: | --- |
| `problems` | *The Problems of Philosophy* | 10 | popular philosophy, general-reader exposition |
| `mysticism` | *Mysticism and Logic and Other Essays* | 8 | abstract opposition, disciplined concession |
| `external-world` | *Our Knowledge of the External World* | 8 | analytic method, polemic against large systems |
| `analysis-mind` | *The Analysis of Mind* | 8 | definition by pressure, conceptual sorting |
| `free-thought` | *Free Thought and Official Propaganda* | 8 | public argument, political example, antithesis |
| `political-ideals` | *Political Ideals* | 8 | humane political reasoning, liberty/coercion balance |

## Paragraph Register

| ID | Source | Line Hint | Rhetorical Move | Calibration Lesson |
| --- | --- | --- | --- | --- |
| `problems-001` | problems | 433 | Relation made concrete through a room example | Define abstractions through ordinary spatial cases. |
| `problems-002` | problems | 436 | Objection to mental production of relations | Use a counterexample before stating the conclusion. |
| `problems-003` | problems | 440 | Chapter problem narrowed after prior conclusion | Let section openings depend on what was just earned. |
| `problems-004` | problems | 442 | Justice used to introduce universals | Make the abstract term answer a familiar question. |
| `problems-005` | problems | 447 | Terminology correction after historical discussion | Replace misleading inherited terms with exact terms. |
| `problems-006` | problems | 709 | Wrong conception split into two causes | Diagnose an error before correcting it. |
| `problems-007` | problems | 711 | Practical prejudice personified | Put a mistaken view into a recognizable human figure. |
| `problems-008` | problems | 713 | Philosophy compared against other studies | State the concession before defending the residual value. |
| `problems-009` | problems | 720 | Low hope kept alive as intellectual duty | Exact uncertainty can strengthen rather than weaken prose. |
| `problems-010` | problems | 723 | Uncertainty turned into value | End with a reversal that changes the reader's valuation. |
| `mysticism-001` | mysticism | 195 | Ethical wish separated from truth-seeking | Keep moral feeling from dictating facts. |
| `mysticism-002` | mysticism | 198 | Mean examples used to test philosophical purity | Let lowly concrete objects discipline high ideals. |
| `mysticism-003` | mysticism | 202 | Shared mystical beliefs enumerated before judgment | Summarize the opponent accurately before critique. |
| `mysticism-004` | mysticism | 206 | Certainty described before belief content | Separate psychological force from propositional truth. |
| `mysticism-005` | mysticism | 227 | Mistaken creed distinguished from useful attitude | Preserve the true part of a false doctrine. |
| `mysticism-006` | mysticism | 230 | Ignorance stated plainly before the thesis | Admit limits, then state the testable claim. |
| `mysticism-007` | mysticism | 232 | False opposition dissolved | Use analysis to convert a binary fight into a relation. |
| `mysticism-008` | mysticism | 263 | Metaphysical whole traced to felt unity | Tie abstract systems back to their motive source. |
| `external-001` | external-world | 66 | Method introduced by capacity and limit | Define a method by what it can and cannot do. |
| `external-002` | external-world | 67 | Personal research pressure made explicit | Let intellectual autobiography justify method without vanity. |
| `external-003` | external-world | 68 | Past systems granted imaginative use but denied truth | Concede usefulness while rejecting authority. |
| `external-004` | external-world | 69 | Scientific aim opposed to temperament | State the institutional standard behind the prose. |
| `external-005` | external-world | 76 | Incompleteness defended as methodological | Use tentativeness as part of construction, not apology. |
| `external-006` | external-world | 97 | Philosophical overclaim framed historically | Begin polemic with a wide claim, then promise repair. |
| `external-007` | external-world | 100 | Three schools distinguished before criticism | Classify before evaluating. |
| `external-008` | external-world | 103 | Galileo analogy for piecemeal results | Use analogy to make method visible. |
| `analysis-001` | analysis-mind | 77 | Common examples open a technical definition | Start with ordinary cases before defining the category. |
| `analysis-002` | analysis-mind | 84 | Popular certainty becomes the object of analysis | Begin with what people think they know. |
| `analysis-003` | analysis-mind | 88 | Thesis placed between false alternatives | Create a third term when a debate is badly framed. |
| `analysis-004` | analysis-mind | 135 | Technical distinction explained in plain terms | Translate a philosophical contrast before using it. |
| `analysis-005` | analysis-mind | 136 | Realism and idealism contrasted symmetrically | Balance opposing views before choosing. |
| `analysis-006` | analysis-mind | 140 | Organic-world claim tested by logic | Expose a seductive metaphor to argumentative pressure. |
| `analysis-007` | analysis-mind | 322 | Instinct and habit distinguished by experience | Draw a practical boundary around a term. |
| `analysis-008` | analysis-mind | 327 | Animal experiment used to teach learning | Use a vivid empirical sequence to ground abstraction. |
| `free-001` | free-thought | 80 | Belief opposed by rational doubt | Build antithesis around a memorable reversal. |
| `free-002` | free-thought | 81 | Scientific method unpacked as social practice | Convert a virtue into a repeatable method. |
| `free-003` | free-thought | 82 | Science contrasted with politics and religion | Use domain contrast to reveal different norms. |
| `free-004` | free-thought | 83 | Dogma linked to material coercion | Show how an intellectual vice becomes social harm. |
| `free-005` | free-thought | 88 | Einstein counterfactual shifted into politics | Use a counterfactual to expose institutional absurdity. |
| `free-006` | free-thought | 90 | Reversal compressed into one sentence | Let the turn carry the paragraph's force. |
| `free-007` | free-thought | 92 | Education critique begins with concrete curriculum | Ground public argument in a schoolroom example. |
| `free-008` | free-thought | 93 | National vanity compared to personal modesty | Use dry social analogy instead of decoration. |
| `political-001` | political-ideals | 77 | Security balanced with creative energy | Refuse a single-condition account of the good. |
| `political-002` | political-ideals | 78 | No final utopia, only living progress | Replace static perfection with active direction. |
| `political-003` | political-ideals | 82 | Institutional atmosphere over reward | Identify the condition that actually changes conduct. |
| `political-004` | political-ideals | 87 | Democratic principle moved into organizations | Transfer an accepted ideal to a neglected case. |
| `political-005` | political-ideals | 89 | Vast state made psychologically remote | Tie political structure to lived impotence. |
| `political-006` | political-ideals | 92 | Liberty bounded by noninterference | State both sides of a principle in the same paragraph. |
| `political-007` | political-ideals | 96 | Beneficent force limited to reducing force | Define a moral exception narrowly. |
| `political-008` | political-ideals | 101 | Legitimate force reduced to cases | Convert political doctrine into conditions. |

## Use In Rewrites

Use this corpus when a passage is compliant but lifeless. Choose one or two reference paragraphs with the same rhetorical mode as the target passage:

- For abstract technical exposition, compare against `problems`, `external-world`, and `analysis-mind`.
- For public argument or institutional critique, compare against `free-thought` and `political-ideals`.
- For passages that must handle an opponent charitably, compare against `mysticism`.

The point is not imitation of diction. The point is paragraph motion: concession, example, distinction, consequence, and turn.
