plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val repoRoot = rootDir.parentFile.parentFile
val poseModelSrc = repoRoot.resolve("models/pose_landmarker_full.task")
val generatedAssets = layout.buildDirectory.dir("generated/assets")

android {
    namespace = "local.visual.corepose"
    compileSdk = 35
    ndkVersion = "28.1.13356709"
    defaultConfig {
        applicationId = "local.visual.corepose"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        ndk {
            abiFilters.clear()
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
        externalNativeBuild {
            cmake {
                cppFlags += "-std=c++17"
                arguments += listOf("-DANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=ON")
            }
        }
    }
    sourceSets {
        getByName("main") {
            assets.srcDir(generatedAssets)
        }
    }
    packaging {
        jniLibs {
            useLegacyPackaging = false
        }
    }
    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    testOptions {
        unitTests.isReturnDefaultValues = true
    }
}

val copyPoseModel by tasks.registering(Copy::class) {
    doFirst {
        if (!poseModelSrc.isFile) {
            throw GradleException(
                "Missing $poseModelSrc. Run: python scripts/download_pose_landmarker.py",
            )
        }
    }
    from(poseModelSrc)
    into(generatedAssets)
}

val localeSrc = repoRoot.resolve("locales/strings.json")
val copyLocaleCatalog by tasks.registering(Copy::class) {
    doFirst {
        if (!localeSrc.isFile) {
            throw GradleException("Missing $localeSrc")
        }
    }
    from(localeSrc)
    into(generatedAssets)
}

val curriculumSrc = repoRoot.resolve("content/ski/curriculum.v2.json")
val copyCurriculum by tasks.registering(Copy::class) {
    doFirst {
        if (!curriculumSrc.isFile) {
            throw GradleException("Missing $curriculumSrc")
        }
    }
    from(curriculumSrc)
    into(generatedAssets)
}

afterEvaluate {
    tasks.matching { it.name.startsWith("merge") && it.name.endsWith("Assets") }.configureEach {
        dependsOn(copyPoseModel, copyLocaleCatalog, copyCurriculum)
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.camera:camera-camera2:1.4.1")
    implementation("androidx.camera:camera-lifecycle:1.4.1")
    implementation("androidx.camera:camera-view:1.4.1")
    implementation("androidx.camera:camera-video:1.4.1")
    implementation("com.google.mediapipe:tasks-vision:0.10.29")
    implementation("com.google.android.material:material:1.12.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}
