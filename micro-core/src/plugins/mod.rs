#[cfg(feature = "debug-telemetry")]
pub mod telemetry;

#[cfg(feature = "debug-telemetry")]
pub use telemetry::{PerfTelemetry, TelemetryPlugin};
