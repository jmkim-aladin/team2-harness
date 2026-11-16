import org.gradle.api.GradleException
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.artifacts.component.ModuleComponentIdentifier
import org.gradle.api.artifacts.component.ProjectComponentIdentifier

class StandaloneAppContractExtension {
    String mode = 'general'
    Set<String> allowedProjectDependencies = [] as Set
    Set<String> allowedRuntimeCoordinates = [] as Set
}

class StandaloneAppContractPlugin implements Plugin<Project> {
    private static final Set<String> IMMUTABLE_DENIED_FAMILIES = [
        'org.springframework',
        'org.hibernate',
        'jakarta.persistence',
        'org.postgresql',
        'software.amazon.awssdk:secretsmanager',
        'org.springframework.ai',
        'com.anthropic',
        'com.openai',
    ].asImmutable()

    private static boolean isProjectIdentifier(identifier) {
        identifier instanceof ProjectComponentIdentifier || identifier.class.name.contains('ProjectComponentIdentifier')
    }

    @Override
    void apply(Project project) {
        project.pluginManager.apply('java')
        def extension = project.extensions.create('standaloneApp', StandaloneAppContractExtension)
        project.tasks.register('verifyStandaloneContract') {
            doLast {
                verify(project, extension)
            }
        }
    }

    private static void verify(Project project, StandaloneAppContractExtension extension) {
        def components = project.configurations.getByName('runtimeClasspath')
            .incoming.resolutionResult.allComponents
        def errors = []
        def rows = []
        def allowedProjects = extension.allowedProjectDependencies.collect { it.toString() } as Set
        def allowedRuntime = extension.allowedRuntimeCoordinates.collect { it.toString() } as Set
        if (!(extension.mode in ['general', 'strict'])) {
            errors << 'STANDALONE_MODE_INVALID'
        }

        components.each { component ->
            def identifier = component.id
            if (identifier instanceof ModuleComponentIdentifier) {
                def coordinate = "${identifier.group}:${identifier.module}:${identifier.version}".toString()
                rows << "module:${coordinate}"
                if (!identifier.group || !identifier.module || !identifier.version) {
                    errors << "ARTIFACT_ORIGIN_UNKNOWN:${identifier.displayName}"
                } else if (IMMUTABLE_DENIED_FAMILIES.any { family -> coordinate.startsWith(family) }) {
                    errors << "CLASSPATH_DENIED_FAMILY:${coordinate}"
                } else if (!allowedRuntime.contains(coordinate)) {
                    errors << "CLASSPATH_NOT_ALLOWLISTED:${coordinate}"
                }
            } else if (identifier instanceof ProjectComponentIdentifier && identifier.projectPath != project.path) {
                def projectPath = identifier.projectPath
                def buildPath = identifier.build.buildPath
                rows << "project:${buildPath}:${projectPath}"
                if (buildPath != ':') {
                    errors << "PROJECT_ORIGIN_UNKNOWN:${buildPath}:${projectPath}"
                } else if (!allowedProjects.contains(projectPath)) {
                    errors << "PROJECT_NOT_ALLOWLISTED:${projectPath}"
                }
            } else if (!(identifier instanceof ProjectComponentIdentifier)) {
                errors << "ARTIFACT_ORIGIN_UNKNOWN:${identifier.displayName}"
            }
        }

        project.configurations.getByName('runtimeClasspath').incoming.artifacts.artifacts.each { artifact ->
            def identifier = artifact.id.componentIdentifier
            def file = artifact.file
            rows << "artifact:${identifier.displayName}:${file}"
            if (!(identifier instanceof ModuleComponentIdentifier) && !isProjectIdentifier(identifier)) {
                errors << "ARTIFACT_ORIGIN_UNKNOWN:${identifier.displayName}"
            } else if (isProjectIdentifier(identifier) && identifier.build.buildPath != ':') {
                errors << "PROJECT_ORIGIN_UNKNOWN:${identifier.build.buildPath}"
            } else if (!file.exists() || (!(isProjectIdentifier(identifier)) && !file.name.endsWith('.jar'))) {
                errors << "ARTIFACT_ORIGIN_UNKNOWN:${identifier.displayName}"
            }
        }

        // A single semantic rule reports once even when both the resolved
        // component identity and its artifact file expose the same violation.
        errors = errors.unique { it.split(':', 2)[0] }

        def report = project.layout.buildDirectory.file('standalone-contract-report.txt').get().asFile
        report.parentFile.mkdirs()
        report.text = (["allowed-runtime:${allowedRuntime}", "allowed-projects:${allowedProjects}"] + rows + (errors ?: ['CONTRACT_PASS'])).join(System.lineSeparator()) + System.lineSeparator()
        if (!errors.isEmpty()) {
            throw new GradleException(errors.join(System.lineSeparator()))
        }
    }
}

class InjectedDeniedPlugin implements Plugin<Project> {
    @Override
    void apply(Project project) {
        project.pluginManager.apply('java')
        project.dependencies.add('runtimeOnly', 'org.springframework:fixture-denied:1.0')
    }
}
