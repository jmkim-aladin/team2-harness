package usecase

import java.nio.file.Files
import java.nio.file.Path

class Bad {
    val bytes = Files.readAllBytes(Path.of("/var/run/lamp/ca.pem"))
}
