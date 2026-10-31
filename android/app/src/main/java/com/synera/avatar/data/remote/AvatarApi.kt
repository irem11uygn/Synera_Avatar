package com.synera.avatar.data.remote

import android.util.Log
import com.synera.avatar.util.t
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.HttpException
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import retrofit2.create
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query
import java.io.IOException
import java.util.concurrent.TimeUnit

interface AvatarApi {
    @POST("api/v1/auth/login")
    suspend fun login(@Body body: LoginRequest): LoginResponse

    @GET("api/v1/sync/pull")
    suspend fun pull(@Header("Authorization") bearer: String, @Query("since") since: Long): PullResponse

    @POST("api/v1/sync/push")
    suspend fun push(@Header("Authorization") bearer: String, @Body body: PushRequest): PushResponse

    @POST("api/v1/auth/logout")
    suspend fun logout(@Header("Authorization") bearer: String): Response<Unit>

    /** Kendi şifresini değiştirir; diğer cihazlardaki oturumlar kapanır, bu oturum sürer. */
    @POST("api/v1/auth/change-password")
    suspend fun changePassword(@Header("Authorization") bearer: String, @Body body: ChangePasswordRequest): UserDto

    /** day boşsa sunucu işletmenin bugününü (yerel saat) kullanır; telefonun saat dilimi yanlış olsa da doğru gün gelir. */
    @GET("api/v1/sync/day-end")
    suspend fun dayEndToday(@Header("Authorization") bearer: String): DayEndDto

    @GET("api/v1/sync/day-end")
    suspend fun dayEnd(@Header("Authorization") bearer: String, @Query("day") day: String): DayEndDto

    @POST("api/v1/stock-counts")
    suspend fun stockCount(@Header("Authorization") bearer: String, @Body body: StockCountRequest): StockCountResponse
}

/** Kullanıcıya gösterilecek API hatası (sunucunun mesajı Türkçedir; ağ hataları seçili dilde). */
class ApiException(message: String, val code: String? = null) : Exception(message)

object ApiClient {
    val json = Json { ignoreUnknownKeys = true }

    fun create(serverUrl: String): AvatarApi {
        val http = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
        return Retrofit.Builder()
            .baseUrl(serverUrl.trimEnd('/') + "/")
            .client(http)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create()
    }

    /** Ağ ve HTTP hatalarını sunucunun Türkçe mesajıyla ApiException'a çevirir. */
    suspend fun <T> call(block: suspend () -> T): T =
        try {
            block()
        } catch (e: HttpException) {
            val body = e.response()?.errorBody()?.string()
            val error = body?.let { runCatching { json.decodeFromString<ApiErrorBody>(it).error }.getOrNull() }
            throw ApiException(error?.message ?: t("Sunucu hatası (HTTP {code}).", "code" to e.code()), error?.code)
        } catch (e: IOException) {
            Log.w(TAG, "Sunucuya ulaşılamadı", e)
            throw ApiException(t("Sunucuya ulaşılamadı. Bağlantıyı ve sunucu adresini kontrol edin."), NETWORK)
        }

    /** Ağ hatası kodu: arka plandaki gönderim bu durumda daha sonra yeniden dener. */
    const val NETWORK = "NETWORK"

    private const val TAG = "AvatarApi"
}
