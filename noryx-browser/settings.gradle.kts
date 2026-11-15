import org.gradle.api.initialization.resolve.RepositoriesMode

pluginManagement {
    repositories {
        google()
        // Google-hosted Maven Central mirror reduces dependence on a single
        // shared Maven Central egress path in CI.
        maven { url = uri("https://maven-central-eu.storage-download.googleapis.com/maven2/") }
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        maven { url = uri("https://maven-central-eu.storage-download.googleapis.com/maven2/") }
        mavenCentral()
    }
}

rootProject.name = "NORYX-Browser"
include(":app")
