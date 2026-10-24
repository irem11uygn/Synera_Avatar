package com.synera.avatar.sync

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.synera.avatar.AvatarApp
import com.synera.avatar.data.remote.ApiException
import java.util.concurrent.TimeUnit

/**
 * Arka planda eşitleme (ADR-003, ADR-004): bekleyen satışları gönderir, sonra sunucudan çeker.
 * Ağ yokken çalışmaz; ağ gelince WorkManager kendiliğinden başlatır, hata olursa artan aralıklarla yeniden dener.
 */
class SyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val repository = (applicationContext as AvatarApp).repository
        if (repository.currentSession() == null) return Result.success() // oturum yok; giriş yapılınca yeniden kurulur
        return try {
            repository.sync()
            Result.success()
        } catch (e: ApiException) {
            // Yetki sorunu yeniden denemekle düzelmez; kullanıcı giriş yapınca ekran eşitler.
            if (e.code == "UNAUTHORIZED" || e.code == "FORBIDDEN") Result.failure() else Result.retry()
        }
    }

    companion object {
        private const val NAME = "satis-gonderimi"

        fun enqueue(context: Context) {
            val request = OneTimeWorkRequestBuilder<SyncWorker>()
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(NAME, ExistingWorkPolicy.APPEND_OR_REPLACE, request)
        }
    }
}
