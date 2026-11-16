import java.nio.file.Files
import java.nio.file.Path

class ExampleEnvironment {
    fun decode(): ExampleSettings {
        val caFile = System.getenv("LAMP_BROKER_CA_FILE")
        val bytes = caFile?.let { Files.readAllBytes(Path.of(it)) }
        return ExampleSettings(bytes)
    }
}
