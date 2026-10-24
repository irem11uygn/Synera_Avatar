package com.synera.avatar.ui.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.synera.avatar.data.remote.ApiException
import com.synera.avatar.data.repo.AvatarRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class LoginUiState(
    val serverUrl: String,
    val username: String = "",
    val password: String = "",
    val loading: Boolean = false,
    val error: String? = null,
)

class LoginViewModel(private val repository: AvatarRepository) : ViewModel() {
    private val _state = MutableStateFlow(LoginUiState(serverUrl = repository.serverUrl))
    val state: StateFlow<LoginUiState> = _state.asStateFlow()

    fun onServerUrlChange(value: String) = _state.update { it.copy(serverUrl = value, error = null) }

    fun onUsernameChange(value: String) = _state.update { it.copy(username = value, error = null) }

    fun onPasswordChange(value: String) = _state.update { it.copy(password = value, error = null) }

    fun onLocalNetworkDenied() = _state.update {
        it.copy(error = "Yerel ağdaki sunucuya bağlanmak için \"Yakındaki cihazlar\" iznine onay vermelisiniz.")
    }

    fun login(onSuccess: () -> Unit) {
        val current = _state.value
        if (current.username.isBlank() || current.password.isBlank()) {
            _state.update { it.copy(error = "Kullanıcı adı ve parola gerekli.") }
            return
        }
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            try {
                repository.login(current.serverUrl, current.username, current.password)
                _state.update { it.copy(loading = false, password = "") }
                onSuccess()
            } catch (e: ApiException) {
                _state.update { it.copy(loading = false, error = e.message) }
            } catch (e: IllegalArgumentException) {
                _state.update { it.copy(loading = false, error = "Sunucu adresi geçersiz (ör. http://10.0.2.2:8000).") }
            }
        }
    }
}
