import java.nio.file.Files
import java.nio.file.LinkOption
import java.nio.file.Path
import java.nio.file.StandardOpenOption
import java.nio.file.attribute.BasicFileAttributes
import java.nio.file.attribute.PosixFilePermission
import java.io.ByteArrayOutputStream

class ExampleEnvironment {
    fun decode(): ExampleSettings {
        val endpoint = System.getenv("LAMP_BROKER_ENDPOINT")
        val caFile = System.getenv("LAMP_BROKER_CA_FILE")?.let(::readValidatedFile)
        return ExampleSettings(endpoint, caFile)
    }
}

private const val MAX_CA_BYTES = 16_384L

internal fun readValidatedFile(path: String): ByteArray {
    val configuredRoot = System.getenv("LAMP_BROKER_CA_ROOT")
        ?: error("LAMP_BROKER_CA_ROOT is required")
    val configuredRootPath = Path.of(configuredRoot)
    require(configuredRootPath.isAbsolute) { "CA root must be absolute" }
    val root = configuredRootPath.normalize()
    require(!Files.isSymbolicLink(root)) { "CA root must not be a symlink" }
    require(Files.isDirectory(root, LinkOption.NOFOLLOW_LINKS)) { "CA root must be a directory" }

    val configuredFile = Path.of(path)
    require(configuredFile.isAbsolute) { "CA file must be absolute" }
    val file = configuredFile.normalize()
    require(file.startsWith(root)) { "CA file is outside the allowed root" }

    // Check every path component, not just the final directory entry. This
    // closes the intermediate-symlink escape while preserving a stable root.
    var cursor = root
    for (component in root.relativize(file)) {
        cursor = cursor.resolve(component)
        require(!Files.isSymbolicLink(cursor)) { "CA file path must not contain symlinks" }
    }

    val attributes = Files.readAttributes(
        file,
        BasicFileAttributes::class.java,
        LinkOption.NOFOLLOW_LINKS,
    )
    require(attributes.isRegularFile) { "CA file must be a regular file" }
    require(attributes.size() <= MAX_CA_BYTES) { "CA file exceeds the maximum size" }

    val permissions = try {
        Files.getPosixFilePermissions(file, LinkOption.NOFOLLOW_LINKS)
    } catch (exception: UnsupportedOperationException) {
        error("CA file permissions cannot be verified")
    }
    require(PosixFilePermission.GROUP_WRITE !in permissions) {
        "CA file must not be group writable"
    }
    require(PosixFilePermission.OTHERS_WRITE !in permissions) {
        "CA file must not be world writable"
    }

    val result = ByteArrayOutputStream(attributes.size().coerceAtMost(MAX_CA_BYTES).toInt())
    Files.newInputStream(file, StandardOpenOption.READ).use { input ->
        val buffer = ByteArray(8_192)
        var total = 0L
        while (true) {
            val read = input.read(buffer)
            if (read < 0) break
            total += read
            require(total <= MAX_CA_BYTES) { "CA file exceeds the maximum size" }
            result.write(buffer, 0, read)
        }
    }
    return result.toByteArray()
}
