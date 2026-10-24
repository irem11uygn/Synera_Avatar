package com.synera.avatar

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.synera.avatar.ui.home.HomeScreen
import com.synera.avatar.ui.home.HomeViewModel
import com.synera.avatar.ui.login.LoginScreen
import com.synera.avatar.ui.login.LoginViewModel
import com.synera.avatar.ui.theme.AvatarTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val repository = (application as AvatarApp).repository

        setContent {
            AvatarTheme {
                Surface(Modifier.fillMaxSize().safeDrawingPadding()) {
                    var token by rememberSaveable { mutableStateOf(repository.currentSession()?.token) }
                    val sessionToken = token
                    if (sessionToken != null) {
                        // Her oturum kendi ViewModel'ini alır; başka kullanıcının verisi taşınmaz.
                        val home = viewModel(key = "home-$sessionToken") { HomeViewModel(repository) }
                        HomeScreen(home, onSignedOut = { token = null })
                    } else {
                        val login = viewModel { LoginViewModel(repository) }
                        LoginScreen(login, onLoggedIn = { token = repository.currentSession()?.token })
                    }
                }
            }
        }
    }
}
