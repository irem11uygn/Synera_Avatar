package com.synera.avatar.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.synera.avatar.data.remote.ApiException
import com.synera.avatar.data.repo.AvatarRepository
import com.synera.avatar.util.PasswordRules
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class PasswordUiState(
    val current: String = "",
    val new: String = "",
    val repeat: String = "",
    val saving: Boolean = false,
    val error: String? = null,
    val done: Boolean = false,
    val signedOut: Boolean = false,
)

/** Şifre değiştirme: kural telefonda denetlenir, sonra sunucuya gider; diğer cihazlardaki oturumlar kapanır. */
class PasswordViewModel(private val repository: AvatarRepository) : ViewModel() {
    private val _state = MutableStateFlow(PasswordUiState())
    val state: StateFlow<PasswordUiState> = _state.asStateFlow()

    fun onCurrentChange(value: String) = _state.update { it.copy(current = value, error = null) }

    fun onNewChange(value: String) = _state.update { it.copy(new = value, error = null) }

    fun onRepeatChange(value: String) = _state.update { it.copy(repeat = value, error = null) }

    fun save() {
        val current = _state.value
        if (current.saving) return
        PasswordRules.problem(current.current, current.new, current.repeat)?.let { problem ->
            _state.update { it.copy(error = problem) }
            return
        }
        _state.update { it.copy(saving = true, error = null) }
        viewModelScope.launch {
            try {
                repository.changePassword(current.current, current.new)
                _state.update { PasswordUiState(done = true) }
            } catch (e: ApiException) {
                _state.update { it.copy(saving = false, error = e.message, signedOut = e.code == "UNAUTHORIZED") }
            }
        }
    }

    /** Geçici şifre ekranından vazgeçmek: oturum sunucuda da kapanır. */
    fun signOut() {
        viewModelScope.launch {
            repository.logout()
            _state.update { it.copy(signedOut = true) }
        }
    }
}
