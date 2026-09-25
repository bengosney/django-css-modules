use pyo3::prelude::*;

/// Placeholder — real css-modules compile lands in task #2.
/// Returns the version string of this native extension.
#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// Native extension backing lightningcss-django.
#[pymodule]
fn _lightningcss_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    Ok(())
}
