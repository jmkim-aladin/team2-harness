class ExampleEnvironment {
    fun decode(): ExampleSettings {
        val name = "LAMP_BROKER_ENDPOINT"
        return ExampleSettings(System.getenv(name))
    }
}
