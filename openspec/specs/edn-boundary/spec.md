# Capability: edn-boundary

The EDN data interchange between Python, ClojureScript, and Rust components of
the BookLogic pipeline. Owns the `read_edn` / `write_edn` reader/writer pair in
`skills/neurosym-forge/scripts/_edn_reader.py` and `_edn_writer.py`, the
`edn-rs` Rust dep, and the contract that `.edn`-extensioned files on disk
carry real EDN syntax — not JSON-stamped-as-EDN.

Spec deltas accumulate here as sprints merge. The current set is empty;
sprints booklogic-cleanup and booklogic-pr5-bermuda-migration add REQs.

## Requirements

_(none yet — sprints merge ADD deltas here)_
