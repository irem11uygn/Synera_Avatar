package com.synera.avatar.data.repo

import android.content.Context
import androidx.core.content.edit
import com.synera.avatar.BuildConfig

data class Session(
    val token: String,
    val username: String,
    val fullName: String,
    val warehouseCode: String?,
)

/**
 * Sunucu adresi ve oturum belirteci, uygulamaya özel SharedPreferences'ta tutulur.
 * Prototip sınırlılığı: belirteç şifrelenmeden saklanır (yalnız bu uygulama okuyabilir).
 */
class SessionStore(context: Context) {
    private val prefs = context.getSharedPreferences("oturum", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString(KEY_SERVER, null) ?: BuildConfig.DEFAULT_SERVER_URL
        set(value) = prefs.edit { putString(KEY_SERVER, value.trim()) }

    fun current(): Session? {
        val token = prefs.getString(KEY_TOKEN, null) ?: return null
        return Session(
            token = token,
            username = prefs.getString(KEY_USERNAME, "").orEmpty(),
            fullName = prefs.getString(KEY_FULL_NAME, "").orEmpty(),
            warehouseCode = prefs.getString(KEY_WAREHOUSE, null),
        )
    }

    fun lastUsername(): String? = prefs.getString(KEY_USERNAME, null)

    fun save(session: Session) = prefs.edit {
        putString(KEY_TOKEN, session.token)
        putString(KEY_USERNAME, session.username)
        putString(KEY_FULL_NAME, session.fullName)
        putString(KEY_WAREHOUSE, session.warehouseCode)
    }

    /** Çıkışta belirteç silinir; kullanıcı adı bir sonraki girişte veri temizliği kararı için kalır. */
    fun clearToken() = prefs.edit { remove(KEY_TOKEN) }

    private companion object {
        const val KEY_SERVER = "server_url"
        const val KEY_TOKEN = "token"
        const val KEY_USERNAME = "username"
        const val KEY_FULL_NAME = "full_name"
        const val KEY_WAREHOUSE = "warehouse_code"
    }
}
