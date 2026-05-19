pub fn render(latex: &str, out_path: &str) -> Result<(), String> {
    let pdf: Vec<u8> = tectonic::latex_to_pdf(latex).map_err(|e| format!("tectonic: {e}"))?;
    std::fs::write(out_path, pdf).map_err(|e| format!("write: {e}"))?;
    Ok(())
}
