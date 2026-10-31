package com.synera.avatar.ui.settings

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.selection.selectable
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.synera.avatar.BuildConfig
import com.synera.avatar.ui.main.MainViewModel
import com.synera.avatar.ui.theme.AppIcons
import com.synera.avatar.ui.theme.Brand
import com.synera.avatar.ui.theme.Panel
import com.synera.avatar.ui.theme.SectionTitle
import com.synera.avatar.util.Dates
import com.synera.avatar.util.L
import com.synera.avatar.util.t

/**
 * Ayarlar: hesap, güvenlik (şifre), eşitleme durumu, dil, uygulama hakkında ve çıkış. Sunucu adresi
 * yalnız giriş ekranında değişir (oturum açıkken değişirse satışlar yanlış sunucuya gidebilirdi).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(viewModel: MainViewModel, onBack: () -> Unit, onChangePassword: () -> Unit, onSignedOut: () -> Unit) {
    val ui by viewModel.ui.collectAsStateWithLifecycle()
    val pending by viewModel.pendingCount.collectAsStateWithLifecycle()
    val meta by viewModel.syncMeta.collectAsStateWithLifecycle()
    var confirmSignOut by remember { mutableStateOf(false) }
    LaunchedEffect(ui.signedOut) { if (ui.signedOut) onSignedOut() }
    BackHandler(onBack = onBack)
    val session = viewModel.session

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(t("Ayarlar")) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(AppIcons.Back, contentDescription = t("Geri")) } },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Brand.Primary,
                    titleContentColor = Color.White,
                    navigationIconContentColor = Color.White,
                ),
            )
        },
    ) { padding ->
        LazyColumn(
            Modifier.padding(padding).fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            item { SectionTitle(t("Hesap")) }
            item {
                Panel {
                    Text(session?.fullName.orEmpty(), style = MaterialTheme.typography.titleSmall)
                    Hint(t("Kullanıcı adı: {name}", "name" to session?.username.orEmpty()))
                    Hint(t("Araç {code}", "code" to session?.warehouseCode.orEmpty()))
                }
            }

            item { SectionTitle(t("Güvenlik")) }
            item {
                Panel(onClick = onChangePassword) {
                    Text(t("Şifremi değiştir"), style = MaterialTheme.typography.titleSmall)
                    Hint(t("En az 8 karakter; harf ve rakam birlikte."))
                }
            }
            item { Hint(t("Oturum anahtarı bu telefonda şifreli saklanır (Android Keystore).")) }

            item { SectionTitle(t("Eşitleme")) }
            item {
                Panel {
                    Hint(t("Sunucu: {url}", "url" to viewModel.serverUrl))
                    Hint(
                        meta?.lastPullAtMillis?.let { t("Son eşitleme: {time}", "time" to Dates.dateTime(it)) }
                            ?: t("Henüz eşitlenmedi."),
                    )
                    Hint(t("Gönderilmeyi bekleyen satış: {n}", "n" to pending))
                }
            }
            item { Hint(t("Sunucu adresi çıkış yapıp giriş ekranında değiştirilir.")) }

            item { SectionTitle(t("Dil")) }
            item {
                Panel {
                    LanguageRow("Türkçe", L.TR)
                    LanguageRow("English", L.EN)
                }
            }

            item { SectionTitle(t("Hakkında")) }
            item {
                Panel {
                    Hint(t("Sürüm {version}", "version" to BuildConfig.VERSION_NAME))
                    Hint(t("Cihaz kimliği: {id}", "id" to viewModel.deviceId))
                    Hint(t("Şifrenizi unuttuysanız yöneticinize başvurun; geçici şifre verir."))
                }
            }

            item {
                OutlinedButton(
                    onClick = { confirmSignOut = true },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                ) { Text(t("Çıkış yap")) }
            }
        }
    }

    if (confirmSignOut) {
        AlertDialog(
            onDismissRequest = { confirmSignOut = false },
            title = { Text(t("Çıkış yapılsın mı?")) },
            text = {
                Text(
                    if (pending > 0) {
                        t("Gönderilmemiş {n} satış var. Telefonda kalır; aynı kullanıcıyla yeniden girince gönderilir.", "n" to pending)
                    } else {
                        t("Oturum sunucuda da kapanır.")
                    },
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    confirmSignOut = false
                    viewModel.logout()
                }) { Text(t("Çıkış yap")) }
            },
            dismissButton = { TextButton(onClick = { confirmSignOut = false }) { Text(t("Vazgeç")) } },
        )
    }
}

@Composable
private fun Hint(text: String) {
    Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
}

@Composable
private fun LanguageRow(label: String, value: String) {
    Row(
        Modifier
            .fillMaxWidth()
            .selectable(selected = L.lang == value, onClick = { L.select(value) }, role = Role.RadioButton)
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RadioButton(selected = L.lang == value, onClick = null)
        Text(label, modifier = Modifier.padding(start = 8.dp))
    }
}
