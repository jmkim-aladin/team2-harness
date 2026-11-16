class ExampleEnvironment {
    fun decode(): ExampleSettings {
        return ExampleSettings(System.getenv())
    }
}
