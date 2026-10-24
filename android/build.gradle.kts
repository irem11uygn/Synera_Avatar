// Kök yapılandırma: eklentiler burada sürümleriyle tanımlanır, app modülünde uygulanır.
// AGP 9 Kotlin'i kendisi derler (built-in Kotlin); ayrıca kotlin-android eklentisi eklenmez.
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.ksp) apply false
}
