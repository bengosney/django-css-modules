use std::path::Path;

use lightningcss::bundler::{Bundler, FileProvider};
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

fn make_targets(browsers_list: Option<Vec<String>>) -> PyResult<Targets> {
    let browsers = match browsers_list {
        Some(list) if !list.is_empty() => Browsers::from_browserslist(list)
            .map_err(|e| PyValueError::new_err(format!("invalid browserslist: {e}")))?,
        _ => None,
    };
    Ok(Targets {
        browsers,
        ..Default::default()
    })
}

/// Compile one CSS Module source to `(code, exports)`.
///
/// `filename` is used verbatim for CSS-modules hashing, so passing a stable key
/// (rather than an absolute path) yields reproducible hashes. `exports` maps each
/// local name to `{"name": <hashed>, "composes": [<hashed>, ...]}`.
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
    let targets = make_targets(browsers_list)?;

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
        .map_err(|e| PyValueError::new_err(format!("failed to parse {filename}: {e}")))?;

    stylesheet
        .minify(MinifyOptions {
            targets,
            ..Default::default()
        })
        .map_err(|e| PyValueError::new_err(format!("failed to minify {filename}: {e}")))?;

    let result = stylesheet
        .to_css(PrinterOptions {
            minify,
            targets,
            ..Default::default()
        })
        .map_err(|e| PyValueError::new_err(format!("failed to print {filename}: {e}")))?;

    let dict = PyDict::new(py);
    if let Some(exports) = result.exports {
        for (local, export) in exports.iter() {
            let entry = PyDict::new(py);
            entry.set_item("name", &export.name)?;
            let composes = PyList::empty(py);
            for reference in &export.composes {
                match reference {
                    CssModuleReference::Local { name } | CssModuleReference::Global { name } => {
                        composes.append(name)?
                    }
                    // Cross-file composes isn't resolved in the single-file path;
                    // keep the referenced local name as a best-effort fallback.
                    CssModuleReference::Dependency { name, .. } => composes.append(name)?,
                }
            }
            entry.set_item("composes", composes)?;
            dict.set_item(local, entry)?;
        }
    }
    Ok((result.code, dict))
}

/// Bundle an entry stylesheet (resolving `@import`) via Lightning CSS's bundler.
///
/// Intended for already-compiled per-file CSS: css-modules is OFF, so class names
/// are preserved verbatim; the bundler only resolves `@import`, dedupes, rebases
/// `url()`, and optimises. Returns the merged CSS.
#[pyfunction]
#[pyo3(signature = (entry, *, minify=true, browsers_list=None))]
fn bundle_entry(entry: &str, minify: bool, browsers_list: Option<Vec<String>>) -> PyResult<String> {
    let targets = make_targets(browsers_list)?;

    let fs = FileProvider::new();
    let mut bundler = Bundler::new(&fs, None, ParserOptions::default());
    let mut stylesheet = bundler
        .bundle(Path::new(entry))
        .map_err(|e| PyValueError::new_err(format!("failed to bundle {entry}: {e}")))?;
    stylesheet
        .minify(MinifyOptions {
            targets,
            ..Default::default()
        })
        .map_err(|e| PyValueError::new_err(format!("failed to minify bundle: {e}")))?;
    let result = stylesheet
        .to_css(PrinterOptions {
            minify,
            targets,
            ..Default::default()
        })
        .map_err(|e| PyValueError::new_err(format!("failed to print bundle: {e}")))?;
    Ok(result.code)
}

/// Native extension backing django-css-modules.
#[pymodule]
fn _lightningcss_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(compile, m)?)?;
    m.add_function(wrap_pyfunction!(bundle_entry, m)?)?;
    Ok(())
}
