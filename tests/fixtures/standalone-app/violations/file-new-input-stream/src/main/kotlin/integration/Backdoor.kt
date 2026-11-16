package integration

import java.nio.file.Files
import java.nio.file.Path

class Backdoor {
    val stream = Files.newInputStream(Path.of("/var/run/lamp/ca.pem"))
}
