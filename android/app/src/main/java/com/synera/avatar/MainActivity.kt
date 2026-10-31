package com.synera.avatar

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.synera.avatar.sync.SyncWorker
import com.synera.avatar.ui.dayend.DayEndViewModel
import com.synera.avatar.ui.login.LoginScreen
import com.synera.avatar.ui.login.LoginViewModel
import com.synera.avatar.ui.main.MainScreen
import com.synera.avatar.ui.main.MainViewModel
import com.synera.avatar.ui.sale.SaleScreen
import com.synera.avatar.ui.sale.SaleViewModel
import com.synera.avatar.ui.settings.PasswordScreen
import com.synera.avatar.ui.settings.PasswordViewModel
import com.synera.avatar.ui.settings.SettingsScreen
import com.synera.avatar.ui.theme.AvatarTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val repository = (application as AvatarApp).repository
        // Önceki açılıştan gönderilmemiş satış kaldıysa bağlantı gelince gönderilsin.
        if (repository.currentSession() != null) SyncWorker.enqueue(this)

        setContent {
            AvatarTheme {
                Surface(Modifier.fillMaxSize().safeDrawingPadding(), color = MaterialTheme.colorScheme.background) {
                    var token by rememberSaveable { mutableStateOf(repository.currentSession()?.token) }
                    var selling by rememberSaveable { mutableStateOf(false) }
                    var saleCount by rememberSaveable { mutableIntStateOf(0) }
                    var settings by rememberSaveable { mutableStateOf(false) }
                    var changingPassword by rememberSaveable { mutableStateOf(false) }
                    var passwordVisit by rememberSaveable { mutableIntStateOf(0) }
                    // Geçici şifreyle girildiyse (ya da yönetici şifreyi sıfırladıysa) önce yeni şifre belirlenir.
                    var mustChange by rememberSaveable { mutableStateOf(repository.currentSession()?.mustChangePassword == true) }
                    val sessionToken = token
                    val signedOut = {
                        token = null
                        settings = false
                        changingPassword = false
                        mustChange = false
                    }
                    when {
                        sessionToken == null -> {
                            val login = viewModel { LoginViewModel(repository) }
                            LoginScreen(login, onLoggedIn = {
                                val session = repository.currentSession()
                                token = session?.token
                                mustChange = session?.mustChangePassword == true
                            })
                        }
                        mustChange || changingPassword -> {
                            // Her açılış temiz bir formla başlar (önceki denemenin şifreleri kalmaz).
                            val password = viewModel(key = "password-$sessionToken-$passwordVisit") { PasswordViewModel(repository) }
                            PasswordScreen(
                                password,
                                forced = mustChange,
                                onDone = {
                                    mustChange = false
                                    changingPassword = false
                                    passwordVisit++
                                },
                                onBack = {
                                    changingPassword = false
                                    passwordVisit++
                                },
                                onSignedOut = signedOut,
                            )
                        }
                        selling -> {
                            // Her yeni satış temiz bir taslakla başlar (önceki satışın durumu taşınmaz).
                            val sale = viewModel(key = "sale-$saleCount") { SaleViewModel(repository) }
                            SaleScreen(sale, onClose = { selling = false })
                        }
                        settings -> {
                            val main = viewModel(key = "main-$sessionToken") { MainViewModel(repository) }
                            SettingsScreen(
                                main,
                                onBack = { settings = false },
                                onChangePassword = { changingPassword = true },
                                onSignedOut = signedOut,
                            )
                        }
                        else -> {
                            // Her oturum kendi ViewModel'ini alır; başka kullanıcının verisi taşınmaz.
                            val main = viewModel(key = "main-$sessionToken") { MainViewModel(repository) }
                            val dayEnd = viewModel(key = "dayend-$sessionToken") { DayEndViewModel(repository) }
                            MainScreen(
                                main,
                                dayEnd,
                                onNewSale = {
                                    saleCount++
                                    selling = true
                                },
                                onSignedOut = signedOut,
                                onOpenSettings = { settings = true },
                                onPasswordRequired = { mustChange = true },
                            )
                        }
                    }
                }
            }
        }
    }
}
