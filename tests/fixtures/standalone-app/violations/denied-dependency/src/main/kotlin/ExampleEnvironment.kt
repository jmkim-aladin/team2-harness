class ExampleEnvironment {
    fun decode(): ExampleSettings {
        val endpoint = System.getenv("LAMP_BROKER_ENDPOINT")
        return ExampleSettings(endpoint)
    }
}
