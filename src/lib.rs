use lightningcss::css_modules::{Config, CssModuleReference, Pattern};
use lightningcss::stylesheet::{MinifyOptions, ParserOptions, PrinterOptions, StyleSheet};
use lightningcss::targets::{Browsers, Targets};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

/// Version string of this native extension.
#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// Compile a CSS Module stylesheet.
///
/// Returns `(code, exports)` where `code` is the transformed CSS and `exports`
/// maps each original local name to `{"name": <hashed>, "composes": [<local>, ...]}`.
/// Cross-file `composes ... from "..."` references are skipped for now (v1.1).
#[pyfunction]
#[pyo3(signature = (css, filename, *, minify=true, browsers_list=None, pattern=None, dashed_idents=false))]
fn compile<'py>(
    py: Python<'py>,
    css: &str,
    filename: &str,
    minify: bool,
    browsers_list: Option<Vec<String>>,
    pattern: Option<String>,
    dashed_idents: bool,
) -> PyResult<(String, Bound<'py, PyDict>)> {
    let browsers = match browsers_list {
        Some(list) if !list.is_empty() => Browsers::from_browserslist(list)
            .map_err(|e| PyValueError::new_err(format!("invalid browserslist: {e}")))?,
        _ => None,
    };
    let targets = Targets {
        browsers,
        ..Default::default()
    };

    // The pattern string must outlive the parsed stylesheet, so keep it owned here.
    let pattern_str = pattern.unwrap_or_else(|| "[hash]_[local]".to_string());
    let pat = Pattern::parse(&pattern_str)
        .map_err(|e| PyValueError::new_err(format!("invalid css modules pattern: {e:?}")))?;

    let parser_options = ParserOptions {
        filename: filename.to_string(),
        css_modules: Some(Config {
            pattern: pat,
            dashed_idents,
            ..Default::default()
        }),
        ..Default::default()
    };

    let mut stylesheet = StyleSheet::parse(css, parser_options)
        .map_err(|e| PyValueError::new_err(format!("failed to parse css: {e}")))?;

    stylesheet
        .minify(MinifyOptions {
            targets,
            ..Default::default()
        })
        .map_err(|e| PyValueError::new_err(format!("failed to minify css: {e}")))?;

    let result = stylesheet
        .to_css(PrinterOptions {
            minify,
            targets,
            ..Default::default()
        })
        .map_err(|e| PyValueError::new_err(format!("failed to print css: {e}")))?;

    let exports_dict = PyDict::new(py);
    if let Some(exports) = result.exports {
        for (local, export) in exports.iter() {
            let entry = PyDict::new(py);
            entry.set_item("name", &export.name)?;
            let composes = PyList::empty(py);
            for reference in &export.composes {
                match reference {
                    // Same-file composes: resolve directly to the composed local name.
                    CssModuleReference::Local { name } => composes.append(name)?,
                    CssModuleReference::Global { name } => composes.append(name)?,
                    // Cross-file `composes x from "./other.module.css"`: deferred to v1.1.
                    CssModuleReference::Dependency { .. } => {}
                }
            }
            entry.set_item("composes", composes)?;
            exports_dict.set_item(local, entry)?;
        }
    }

    Ok((result.code, exports_dict))
}

/// Native extension backing lightningcss-django.
#[pymodule]
fn _lightningcss_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(compile, m)?)?;
    Ok(())
}
