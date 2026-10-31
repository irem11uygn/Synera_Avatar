package com.synera.avatar.ui.settings

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.synera.avatar.ui.theme.AppIcons
import com.synera.avatar.ui.theme.Banner
import com.synera.avatar.ui.theme.Brand
import com.synera.avatar.ui.theme.Tone
import com.synera.avatar.util.t

/**
 * Şifre ekranı. forced: yöneticinin verdiği geçici şifreyle girildi; sunucu yeni şifre belirlenmeden
 * eşitlemeye izin vermez, bu yüzden geri dönülemez (yalnız çıkış yapılabilir).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PasswordScreen(
    viewModel: PasswordViewModel,
    forced: Boolean,
    onDone: () -> Unit,
    onBack: () -> Unit,
    onSignedOut: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(state.done) { if (state.done) onDone() }
    LaunchedEffect(state.signedOut) { if (state.signedOut) onSignedOut() }
    BackHandler(enabled = !forced, onBack = onBack)

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(if (forced) t("Yeni şifrenizi belirleyin") else t("Şifremi değiştir")) },
                navigationIcon = {
                    if (!forced) IconButton(onClick = onBack) { Icon(AppIcons.Back, contentDescription = t("Geri")) }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Brand.Primary,
                    titleContentColor = Color.White,
                    navigationIconContentColor = Color.White,
                ),
            )
        },
    ) { padding ->
        Column(
            Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (forced) {
                Banner(
                    t("Yöneticinin verdiği geçici şifreyle giriş yaptınız. Devam etmek için kendi şifrenizi belirleyin."),
                    Tone.WARNING,
                )
            }
            PasswordField(state.current, viewModel::onCurrentChange, if (forced) t("Geçici şifre") else t("Mevcut şifre"))
            PasswordField(state.new, viewModel::onNewChange, t("Yeni şifre"))
            PasswordField(state.repeat, viewModel::onRepeatChange, t("Yeni şifre (tekrar)"))
            Text(
                t("En az 8 karakter; harf ve rakam birlikte. Değişince diğer cihazlardaki oturumlarınız kapanır."),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            Button(onClick = viewModel::save, enabled = !state.saving, modifier = Modifier.fillMaxWidth()) {
                Text(if (state.saving) t("Kaydediliyor…") else t("Şifreyi kaydet"))
            }
            if (forced) {
                TextButton(onClick = viewModel::signOut, modifier = Modifier.fillMaxWidth()) { Text(t("Çıkış yap")) }
            }
        }
    }
}

@Composable
private fun PasswordField(value: String, onChange: (String) -> Unit, label: String) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        singleLine = true,
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        modifier = Modifier.fillMaxWidth(),
    )
}
