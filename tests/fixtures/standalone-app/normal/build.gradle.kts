plugins {
    id("lamp.standalone-app")
}

standaloneApp {
    isolation.set("strict")
    allowedProjectDependencies.set(setOf(":adapters:worker-runtime"))
    allowedRuntimeCoordinates.set(setOf(
        "com.squareup.okhttp3:okhttp:4.12.0",
        "tools.jackson.core:jackson-databind:3.1.7",
    ))
}

application {
    mainClass.set("ExampleApplicationKt")
}

dependencies {
    implementation(project(":adapters:worker-runtime"))
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("tools.jackson.core:jackson-databind:3.1.7")
}
