/* A dylib that exports none of the plugin interface: the host must skip it. */
int not_a_plugin(void) { return 42; }
