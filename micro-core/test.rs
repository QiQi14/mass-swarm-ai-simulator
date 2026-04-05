fn foo(
    #[cfg(feature = "test-feat")]
    a: u32,
    b: u32,
) {}

fn main() {
    foo(2);
}
