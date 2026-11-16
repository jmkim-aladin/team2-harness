fun main(args: Array<String>) {
    val cases = args.singleOrNull()
        ?.split(',')
        ?.filter(String::isNotBlank)
        ?: error("security probe cases are required")

    for (entry in cases) {
        val separator = entry.indexOf('=')
        require(separator > 0) { "case must be name=path" }
        val name = entry.substring(0, separator)
        val path = entry.substring(separator + 1)
        try {
            val bytes = readValidatedFile(path)
            println("CASE:$name:READ_OK:${bytes.size}")
        } catch (exception: Exception) {
            println("CASE:$name:SECURE_FILE_REJECTED:${exception.message}")
        }
    }
}
