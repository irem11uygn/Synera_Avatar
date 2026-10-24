package com.synera.avatar

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.synera.avatar.sync.SyncWorker
import com.synera.avatar.ui.home.HomeScreen
import com.synera.avatar.ui.home.HomeViewModel
import com.synera.avatar.ui.login.LoginScreen
import com.synera.avatar.ui.login.LoginViewModel
import com.synera.avatar.ui.sale.SaleScreen
import com.synera.avatar.ui.sale.SaleViewModel
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
                Surface(Modifier.fillMaxSize().safeDrawingPadding()) {
                    var token by rememberSaveable { mutableStateOf(repository.currentSession()?.token) }
                    var selling by rememberSaveable { mutableStateOf(false) }
                    var saleCount by rememberSaveable { mutableIntStateOf(0) }
                    val sessionToken = token
                    when {
                        sessionToken == null -> {
                            val login = viewModel { LoginViewModel(repository) }
                            LoginScreen(login, onLoggedIn = { token = repository.currentSession()?.token })
                        }
                        selling -> {
                            // Her yeni satış temiz bir taslakla başlar (önceki satışın durumu taşınmaz).
                            val sale = viewModel(key = "sale-$saleCount") { SaleViewModel(repository) }
                            SaleScreen(sale, onClose = { selling = false })
                        }
                        else -> {
                            // Her oturum kendi ViewModel'ini alır; başka kullanıcının verisi taşınmaz.
                            val home = viewModel(key = "home-$sessionToken") { HomeViewModel(repository) }
                            HomeScreen(
                                home,
                                onNewSale = {
                                    saleCount++
                                    selling = true
                                },
                                onSignedOut = { token = null },
                            )
                        }
                    }
                }
            }
        }
    }
}
