//! Z3-variable-name algorithm. Mirrors Python
//! `_canonical.canonical_var_name` and CLJS `canonical-var-name`. The
//! golden test vectors at
//! `skills/neurosym-forge/tests/golden/canonical_var_name.edn` are the
//! cross-language source of truth.
//!
//! REQ-EDN-046 (Rust implementation).

pub fn canonical_var_name(predicate: &str, subject: &str) -> String {
    let pred = predicate.trim_start_matches(|c: char| c == ':' || c == '?');
    let subj = subject.trim_start_matches(|c: char| c == ':' || c == '?');
    format!("{pred}_{subj}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_colon_prefix() {
        assert_eq!(canonical_var_name(":foo", ":bar"), "foo_bar");
    }

    #[test]
    fn strips_question_prefix() {
        assert_eq!(canonical_var_name("?foo", "?bar"), "foo_bar");
    }

    #[test]
    fn keeps_bare_identifier() {
        assert_eq!(canonical_var_name("foo", "bar"), "foo_bar");
    }

    #[test]
    fn mixed_prefixes() {
        assert_eq!(canonical_var_name(":pred", "?subj"), "pred_subj");
        assert_eq!(canonical_var_name("?pred", ":subj"), "pred_subj");
    }
}
